import json
import re

import asyncpg
import mo_sql_parsing

import querydb
from analyzer.command import Command
from domain.entities.query import Query
from domain.entities.suggestion import Suggestion


# noinspection SqlNoDataSourceInspection,SqlDialectInspection
class MaterializedViewCommand(Command):
    _original: Query
    _suggestion: Suggestion
    _conn: asyncpg.pool.Pool

    _queries: querydb.QueryDB

    _table: str
    _apply_sql: str
    _create_cost_sql: str
    _update_cost_sql: str
    _create_cost: float | None = None

    def __init__(self, suggestion: Suggestion, queries: querydb.QueryDB, conn: asyncpg.pool.Pool):
        self._original = suggestion.queries[0]
        self._suggestion = suggestion
        self._conn = conn
        self._queries = queries
        self._apply_sql = self._format_hypothetical_view(suggestion.action.command)

    def name(self) -> str:
        return self._suggestion.action.name

    def suggestion(self) -> Suggestion:
        return self._suggestion

    # Creates the hypothetical index and returns the cumulative gains
    # by executing the queries affected by it with the `explain` clause.
    async def apply(self) -> tuple[dict[str, float], float, float]:
        # Get queries total cost
        old_cost = await self._old_query_cost()
        new_cost = await self._new_query_cost()

        gain = old_cost - new_cost

        uid = self._suggestion.queries[0].id

        # Replace query reference
        self._queries.replace(uid, Query(
            id=self._suggestion.queries[0].id,
            raw="select 1",
            plan=None,
            runs=self._suggestion.queries[0].runs,
        ))

        return {uid: gain}, gain, 1

    # Drops the created hypothetical index. *MUST* be called after `apply`.
    async def rollback(self) -> None:
        # Check if apply was called before. If not, raise an exception.
        self._queries.replace(self._original.id, self._original)

        return

    def description(self) -> str:
        return f"{self._suggestion.action.name}: {self._suggestion.action.command}"

    async def _old_query_cost(self) -> float:
        query = self._format_explain(self._suggestion.queries[0].raw)
        record: asyncpg.Record = await self._conn.fetchval(query)
        plan = json.loads(record)
        return self._suggestion.queries[0].runs*plan[0]["Plan"]["Total Cost"]

    async def _new_query_cost(self) -> float:
        query = self._format_explain(self._apply_sql)
        record: asyncpg.Record = await self._conn.fetchval(query)
        plan = json.loads(record)
        return self._suggestion.queries[0].runs*(plan[0]["Plan"]["Total Cost"]-plan[0]["Plan"]["Startup Cost"])

    def _format_hypothetical_view(self, query: str) -> str:
        query = query.replace("'", "''").replace(";", "")
        query = re.sub(pattern="create materialized view .* as", repl="", string=query)
        conds = self._extract_extra_conditions(query)
        s = f"""
        with mv as materialized({query})
        select mv.* from mv
        """
        if conds != "":
            s = s + " where " + conds

        return s + ";"

    @staticmethod
    def _format_explain(query: str) -> str:
        query = query.replace(";", "")
        return f"explain (format json) {query};"

    def _extract_extra_conditions(self, mview_query: str) -> str:
        def normalize(d: dict) -> dict:
            n = {}

            if "and" not in d:
                d = {"and": [d]}

            for cond in d["and"]:
                for k, v in cond.items():
                    n[v[0]] = {"op": k, "v": v[1]}

            return n

        def reverse(d: dict) -> dict:
            n = {"and": []}

            for k, v in d.items():
                n["and"].append({v["op"]: [k, v["v"]]})

            if len(d) == 1:
                return n["and"][0]

            return n

        mview = mo_sql_parsing.parse(mview_query)["where"]
        mview = normalize(mview)
        query = mo_sql_parsing.parse(self._original.raw)["where"]
        query = normalize(query)

        diff = {}
        for k, v in query.items():
            if k in mview:
                continue
            diff[k] = v

        return mo_sql_parsing.format(reverse(diff))

