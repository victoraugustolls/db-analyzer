import json
from functools import reduce

import asyncpg

from analyzer.command import Command
from domain.entities.suggestion import Suggestion


class IndexCommand(Command):
    _suggestion: Suggestion
    _conn: asyncpg.pool.Pool

    _apply_sql: str
    _rollback_sql: str
    _hypo_index_id: int | None

    def __init__(self, suggestion: Suggestion, conn: asyncpg.pool.Pool):
        self._suggestion = suggestion
        self._conn = conn
        self._apply_sql = self._format_hypothetical_index(suggestion.action.command)
        self._rollback_sql = "select * from hypopg_drop_index($1);"

    # Creates the hypothetical index and returns the cumulative gains
    # by executing the queries affected by it with the `explain` clause.
    async def apply(self) -> tuple[int, int]:
        # Get current queries total cost
        old_cost = await self._extract_queries_cost()

        # Create hypothetical index and return its id
        row: asyncpg.Record = await self._conn.fetchrow(self._apply_sql)
        self._hypo_index_id = row[0]

        # Check gains on the queries associated with the index
        new_cost = await self._extract_queries_cost()

        return old_cost - new_cost, 1

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

    async def _extract_queries_cost(self) -> int:
        cost = 0
        for query in self._suggestion.queries:
            record: asyncpg.Record = await self._conn.fetchval(self._format_explain(query.raw))
            plan = json.loads(record)
            cost += plan[0]["Plan"]["Total Cost"]

        return cost

    @staticmethod
    def _format_hypothetical_index(query: str) -> str:
        query = query.replace("'", "''").replace(";", "")
        return f"select indexrelid from hypopg_create_index('{query}');"

    @staticmethod
    def _format_explain(query: str) -> str:
        query = query.replace(";", "")
        return f"explain (format json) {query};"
