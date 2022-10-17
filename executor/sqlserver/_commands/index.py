import aioodbc

import analyzer
import querydb
import domain


# noinspection SqlNoDataSourceInspection,SqlDialectInspection
class Index(analyzer.Command):
    _suggestion: domain.Suggestion
    _conn: aioodbc.Connection

    _queries: querydb.QueryDB

    _apply_sql: str
    _rollback_sql: str
    _create_cost_sql: str
    _update_cost_sql: str
    _hypo_index_name: str | None = None
    _create_cost: float | None = None

    def __init__(self, suggestion: domain.Suggestion, queries: querydb.QueryDB, conn: aioodbc.Connection):
        self._suggestion = suggestion
        self._conn = conn
        self._queries = queries
        self._hypo_index_name = self._extract_index_name(suggestion.action.command)
        self._apply_sql = self._format_hypothetical_index(suggestion.action.command)
        self._rollback_sql = "select * from hypopg_drop_index($1);"

    def name(self) -> str:
        return self._suggestion.action.name

    def suggestion(self) -> domain.Suggestion:
        return self._suggestion

    # Creates the hypothetical index and returns the cumulative gains
    # by executing the queries affected by it with the `explain` clause.
    async def apply(self) -> tuple[dict[str, float], float, float]:
        # Get current queries total cost
        old_costs_per_query, old_queries_cost = await self._extract_queries_cost()

        # Create hypothetical index and activate it
        async with self._conn.cursor() as cur:
            print("Will create index")
            await cur.execute(self._apply_sql)
            _ = await cur.fetchone
            print("Will create index activate command")
            activate = (
                "SELECT N'DBCC AUTOPILOT(0,' + CONVERT(nvarchar(MAX), DB_ID()) +  N',' + CONVERT(nvarchar(MAX), object_id) + N',' + CONVERT(nvarchar(MAX), index_id) +  N');'" +
                " FROM sys.indexes" +
                f" WHERE name = {self._hypo_index_name}"
            )
            await cur.execute(activate)
            activate_return: dict = await cur.fetchone()
            print("Activate return:", activate_return)

        # Check gains on the queries associated with the index
        new_costs_per_query, new_queries_cost = await self._extract_queries_cost()

        # Calculate gains for each query
        queries_gain: dict[str, float] = {}
        for query, cost in old_costs_per_query.items():
            queries_gain[query] = cost - new_costs_per_query[query]

        return queries_gain, old_queries_cost - new_queries_cost, 1

    # Drops the created hypothetical index. *MUST* be called after `apply`.
    async def rollback(self) -> None:
        # Check if apply was called before. If not, raise an exception.
        if self._hypo_index_name is None:
            raise Exception("apply must be called before rollback")

        # Drop hypothetical index and reset its id.
        await self._rollback_command()
        self._hypo_index_name = None

        return

    def description(self) -> str:
        return f"{self._suggestion.action.name}: {self._suggestion.action.command}"

    async def _extract_queries_cost(self) -> tuple[dict[str, float], float]:
        cost = 0

        queries_cost: dict[str, float] = {}

        async with self._conn.cursor() as cur:
            await cur.execute('SET AUTOPILOT ON;')
            _ = await cur.fetchone()
            for query in self._queries.queries():
                await cur.execute(query.raw)
                record: dict = await cur.fetchone()
                print(record)
            await cur.execute('SET AUTOPILOT OFF;')
            _ = await cur.fetchone()

        return queries_cost, cost

    async def _rollback_command(self):
        get_drop = (
            "SELECT N'DROP INDEX ' + QUOTENAME(name) + N' ON ' + QUOTENAME(OBJECT_SCHEMA_NAME(object_id)) + N'.' + QUOTENAME(OBJECT_NAME(object_id)) + N';'" +
            " FROM sys.indexes" +
            f" WHERE name = '{self._hypo_index_name}'"
        )

        async with self._conn.cursor() as cur:
            await cur.execute(get_drop)
            record: dict = await cur.fetchone()
            print("Drop:", record)

    @staticmethod
    def _extract_index_name(query: str) -> str:
        index_name = query.split("[", maxsplit=1)[1].split("]", maxsplit=1)[0]
        print("Index name:", index_name)
        return index_name

    @staticmethod
    def _format_hypothetical_index(query: str) -> str:
        query = query.replace(";", "")
        return f"{query} with statistics_only = -1;"
