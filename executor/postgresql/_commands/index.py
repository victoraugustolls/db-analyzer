import json

import asyncpg

import analyzer
import querydb
import domain


# noinspection SqlNoDataSourceInspection,SqlDialectInspection
class Index(analyzer.Command):
    _suggestion: domain.Suggestion
    _conn: asyncpg.pool.Pool

    _queries: querydb.QueryDB

    _table: str
    _apply_sql: str
    _rollback_sql: str
    _create_cost_sql: str
    _update_cost_sql: str
    _hypo_index_id: int | None = None
    _create_cost: float | None = None

    def __init__(self, suggestion: domain.Suggestion, queries: querydb.QueryDB, conn: asyncpg.pool.Pool):
        self._suggestion = suggestion
        self._conn = conn
        self._queries = queries
        self._table = self._extract_table_name_from_query(suggestion.action.command)
        self._apply_sql = self._format_hypothetical_index(suggestion.action.command)
        self._rollback_sql = "select * from hypopg_drop_index($1);"
        self._create_cost_sql = self._format_creation_cost_query(suggestion.action.command)
        self._update_cost_sql = self._format_update_cost_query(suggestion.action.command)

    def name(self) -> str:
        return self._suggestion.action.name

    def suggestion(self) -> domain.Suggestion:
        return self._suggestion

    # Creates the hypothetical index and returns the cumulative gains
    # by executing the queries affected by it with the `explain` clause.
    async def apply(self) -> tuple[dict[str, float], float, float]:
        # Get current queries total cost
        old_costs_per_query, old_queries_cost = await self._extract_queries_cost()

        # Create hypothetical index and return its id
        row: asyncpg.Record = await self._conn.fetchrow(self._apply_sql)
        self._hypo_index_id = row[0]

        # Check gains on the queries associated with the index
        new_costs_per_query, new_queries_cost = await self._extract_queries_cost()

        # Calculate gains for each query
        queries_gain: dict[str, float] = {}
        for query, cost in old_costs_per_query.items():
            queries_gain[query] = cost - new_costs_per_query[query]

        return queries_gain, old_queries_cost - new_queries_cost, await self._total_index_cost()

    # Drops the created hypothetical index. *MUST* be called after `apply`.
    async def rollback(self) -> None:
        # Check if apply was called before. If not, raise an exception.
        if self._hypo_index_id is None:
            raise Exception("apply must be called before rollback")

        # Drop hypothetical index and reset its id.
        await self._conn.execute(self._rollback_sql, self._hypo_index_id)
        self._hypo_index_id = None

        return

    def description(self) -> str:
        return f"{self._suggestion.action.name}: {self._suggestion.action.command}"

    async def _extract_queries_cost(self) -> tuple[dict[str, float], float]:
        cost = 0
        queries_cost: dict[str, float] = {}
        # TODO: run all queries
        for query in self._queries.queries():
            record: asyncpg.Record = await self._conn.fetchval(self._format_explain(query.raw))
            plan = json.loads(record)
            query_cost = query.runs*plan[0]["Plan"]["Total Cost"]
            queries_cost[query.id] = query_cost
            cost += query_cost

        return queries_cost, cost

    @staticmethod
    def _format_hypothetical_index(query: str) -> str:
        query = query.replace("'", "''").replace(";", "")
        return f"select indexrelid from hypopg_create_index('{query}');"

    @staticmethod
    def _format_explain(query: str) -> str:
        query = query.replace(";", "")
        return f"explain (format json) {query};"

    async def _total_index_cost(self) -> float:
        return await self._get_creation_cost() + await self._get_update_cost()

    async def _get_creation_cost(self) -> float:
        if self._create_cost is not None:
            return self._create_cost

        record: asyncpg.Record = await self._conn.fetchval(self._create_cost_sql)
        self._create_cost = record
        return record

    async def _get_update_cost(self) -> float:
        record: asyncpg.Record = await self._conn.fetchval(self._update_cost_sql)
        queries = self._queries.with_table(self._table)
        if queries is None:
            return 0

        self._update_cost = record * len(queries)
        return self._update_cost

    @staticmethod
    def _extract_table_name_from_query(query: str) -> str:
        split = query.split(" on ")
        if len(split) != 2:
            raise Exception("invalid index creation command")

        split = split[1].split("(")
        if len(split) != 2:
            raise Exception("invalid index creation command")

        # removing schema name if present
        split = split[0].split(".")
        if len(split) == 1:
            return split[0].strip()

        return split[1].strip()

    def _format_creation_cost_query(self, query: str) -> str:
        table_name = self._extract_table_name_from_query(query)

        return f"""
        select 2*relpages+0.01*reltuples*log(reltuples)
        from pg_class
        where relname = '{table_name}';
        """

    def _format_update_cost_query(self, query: str) -> str:
        table_name = self._extract_table_name_from_query(query)

        return f"""
        select (2*relpages)/reltuples+0.01
        from pg_class
        where relname = '{table_name}';
        """
