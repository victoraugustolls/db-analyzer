import asyncpg

import analyzer
import config
import domain
import querydb
from . import _commands
from ..executor import Executor


class PostgreSQL(Executor):
    _analyzer: analyzer.Analyzer
    _pool: asyncpg.Pool
    _queries: querydb.QueryDB

    def __init__(self, pool: asyncpg.Pool, queries: querydb.QueryDB) -> None:
        self._analyzer = analyzer.Analyzer()
        self._pool = pool
        self._queries = queries

    @classmethod
    async def create(cls, dsn: config.DSN, queries: querydb.QueryDB) -> "PostgreSQL":
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
    async def prepare(self, schema: domain.Schema) -> list[domain.Suggestion]:
        return []

    """
    New actions might appear given a query, depending on the RDBMS.
    In the PostgreSQL case, this is useful for applying the postgres loose index scan strategy.
    """
    async def analyze(self, query: domain.Query) -> list[domain.Action]:
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
    async def execute(self, suggestions: [domain.Suggestion], schema: domain.Schema) -> analyzer.Node:
        cmds: list[analyzer.Command] = []
        for suggestion in suggestions:
            # TODO: refactor to use as enum
            if suggestion.action.type_ == domain.ActionType.INDEX.value:
                cmds.append(_commands.Index(suggestion=suggestion, conn=self._pool, queries=self._queries))
            elif suggestion.action.type_ == domain.ActionType.MATERIALIZED_VIEW.value:
                cmds.append(_commands.MaterializedView(suggestion=suggestion, conn=self._pool, queries=self._queries))
            else:
                continue

        return await self._analyzer.generate(actions=cmds)
