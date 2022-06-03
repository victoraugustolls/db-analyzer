import json

import asyncpg

import querydb
from domain.entities.action import Action, ActionType
from domain.entities.query import Query
from domain.entities.result import ActionResult, SuggestionResult
from domain.entities.schema import Schema, Column
from domain.entities.suggestion import Suggestion
from vos import DSN
from .column_tetris import zero_values
from .commands.index import IndexCommand
from .commands.materialized_view import MaterializedViewCommand
from analyzer.analyzer import Analyzer
from analyzer.command import Command
from analyzer.node import Node
from analyzer.result import Result


class PostgreSQLExecutor:
    _analyzer: Analyzer
    _pool: asyncpg.Pool
    _queries: querydb.QueryDB

    def __init__(self, pool: asyncpg.Pool, queries: querydb.QueryDB) -> None:
        self._analyzer = Analyzer()
        self._pool = pool
        self._queries = queries

    @classmethod
    async def create(cls, dsn: DSN, queries: querydb.QueryDB) -> "PostgreSQLExecutor":
        pool: asyncpg.Pool = await asyncpg.create_pool(
            dsn=f"postgresql://{dsn.user}:{dsn.password}@{dsn.host}:{dsn.port}/{dsn.database}",
        )

        return cls(pool=pool, queries=queries)

    """
    New suggestions might appear given a schema, depending on the RDBMS.
    In the PostgreSQL case, this is useful for applying the column tetris strategy.
    
    More about in the following links:
    - https://www.2ndquadrant.com/en/blog/on-rocks-and-sand/
    - https://stackoverflow.com/questions/2966524/calculating-and-saving-space-in-postgresql
    """

    async def prepare(self, schema: Schema) -> list[Suggestion]:
        return []
        # pg_types: dict[str, int] = {}
        # suggestions: list[Suggestion] = []
        #
        # # Fill postgres types information for column tetris
        # records: list[asyncpg.Record] = await self._pool.fetch("select typname, typlen from pg_type;")
        # for record in records:
        #     pg_types[record[0]] = record[1]
        #
        # for table in schema.tables:
        #     # dict of column size to (column_name, column_type)
        #     sizes: dict[int, Column] = {}
        #
        #     for column in table.columns:
        #         size = pg_types[column.type]
        #         # Might be a custom type
        #         if size is None:
        #             sizes = {}
        #             break
        #
        #         sizes[size] = column
        #
        #     # In the case of missing type, don't try to optimize table column order
        #     if len(sizes) == 0:
        #         continue
        #
        #     # Sort key sizes and check if optimized order is equal to original order and build command for execution
        #     columns: list[str] = []
        #     old_row: str = "pg_column_size(row("
        #     new_row: str = "pg_column_size(row("
        #     keys = sorted(sizes.keys(), reverse=True)
        #     for i in range(len(keys)):
        #         if sizes[keys[i]].name == table.columns[i].name:
        #             continue
        #
        #         old_row += f"{zero_values[table.columns[i].type]}::{table.columns[i].type},"
        #         new_row += f"{zero_values[sizes[keys[i]].type]}::{sizes[keys[i]].type},"
        #         columns.append(f"{sizes[keys[i]].name}::{sizes[keys[i]].type}")
        #
        #     old_row = old_row.removesuffix(",") + "))"
        #     new_row = new_row.removesuffix(",") + "))"
        #
        #     suggestions.append(Suggestion(
        #         action=Action(
        #             name=table.name,
        #             type_=ActionType.COLUMN_TETRIS.value,
        #             command=f"select {old_row}, {new_row};",
        #         ),
        #         queries=[Query(
        #             id=f"column_tetris_{table.name}",
        #             raw=f'({", ".join(columns)})',
        #             runs=1,
        #             plan=None,
        #         )],
        #     ))
        #
        # return suggestions

    """
    New actions might appear given a query, depending on the RDBMS.
    In the PostgreSQL case, this is useful for applying the postgres loose index scan strategy.
    """

    async def analyze(self, query: Query) -> list[Action]:
        pass

    """
    Should execute all the actions for a given suggestion, finding the best possible combination.
    The final result can contain between one (1) and N actions, being N the number of suggestions provided.
    The result message must also explain the reason for the actions selection.
    
    Focus first on indexes only. Execute the following steps for each suggested index:
    1. Create a hypothetical index using HypoPG (https://github.com/HypoPG/hypopg)
    2. Generate a new plan using bare `EXPLAIN`
    3. Check the delta between the original plan cost and the new one
    
    Sort the result by delta and return the best index to be created.
    """

    async def execute(self, suggestions: [Suggestion], schema: Schema) -> Result:
        commands: list[Command] = []
        for suggestion in suggestions:
            if suggestion.action.type_ == ActionType.INDEX.value:
                commands.append(IndexCommand(suggestion=suggestion, conn=self._pool, queries=self._queries))
            elif suggestion.action.type_ == ActionType.MATERIALIZED_VIEW.value:
                commands.append(MaterializedViewCommand(suggestion=suggestion, conn=self._pool, queries=self._queries))
            else:
                continue

        return await self._analyzer.generate(actions=commands)

        # results: list[ActionResult] = []
        #
        # for suggestion in suggestions:
        #     action = suggestion.action
        #     # We only accept index actions for now
        #     match action.type_:
        #         case ActionType.INDEX.value:
        #             result = await self._process_index_action(action=action, queries=suggestion.queries)
        #         case ActionType.COLUMN_TETRIS.value:
        #             result = await self._process_column_tetris_action(action=action, query=suggestion.queries[0])
        #         case _:
        #             continue
        #
        #     results.append(result)
        #
        # results.sort(key=lambda r: r.delta, reverse=True)
        # return SuggestionResult(actions=results, query=[], message=results[0].message)

    async def _process_index_action(self, queries: [Query], action: Action) -> ActionResult:
        total_cost = 0
        for query in queries:
            total_cost += query.plan.cost

        new_total_cost = 0

        await self._pool.execute(query=self._format_hypothetical_index(action.command))

        for query in queries:
            record: asyncpg.Record = await self._pool.fetchval(query=self._format_explain(query.raw))
            plan = json.loads(record)
            cost = plan[0]["Plan"]["Total Cost"]
            new_total_cost += cost
            self._db.add_query_action(query=query.id, action=action)

        await self._pool.execute(query="select hypopg_reset();")

        delta = total_cost - new_total_cost

        message = f"The query cost can be reduced by {delta}, " \
                  f"from {total_cost} to {new_total_cost}, by creating the index '{action.name}'."

        self._db.add_action(Result(action=action, queries={q for q in queries}, delta=delta))

        return ActionResult(action=action, new_cost=new_total_cost, old_cost=total_cost, message=message)

    async def _process_column_tetris_action(self, action: Action, query: Query) -> ActionResult:
        record: asyncpg.Record = await self._pool.fetchrow(query=action.command)

        old_size = record[0]
        new_size = record[1]

        message = f"The table '{action.name}' row size can be reduced by {old_size - new_size} bytes, " \
                  f"from {old_size} to {new_size}, by reordering the columns to: {query.raw}."

        return ActionResult(action=action, new_cost=new_size, old_cost=old_size, message=message)

    @staticmethod
    def _format_hypothetical_index(query: str) -> str:
        query = query.replace("'", "''").replace(";", "")
        return f"select * from hypopg_create_index('{query}');"

    @staticmethod
    def _format_explain(query: str) -> str:
        query = query.replace(";", "")
        return f"explain (format json) {query};"
