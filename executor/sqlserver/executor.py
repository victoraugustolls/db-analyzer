import aioodbc

import analyzer
import config
import domain
import querydb
from . import _commands
from ..executor import Executor


class SQLServer(Executor):
    _analyzer: analyzer.Analyzer
    _pool: aioodbc.Connection
    _queries: querydb.QueryDB

    def __init__(self, pool: aioodbc.Connection, queries: querydb.QueryDB) -> None:
        self._analyzer = analyzer.Analyzer()
        self._pool = pool
        self._queries = queries

    @classmethod
    async def create(cls, dsn: config.DSN, queries: querydb.QueryDB) -> "SQLServer":
        pool: aioodbc.Connection = await aioodbc.connect(
            dsn="DRIVER=FreeTDS;" +
                f"SERVER={dsn.host}:{dsn.port};DATABASE={dsn.port};UID={dsn.user};PWD={dsn.password}",
        )

        return cls(pool=pool, queries=queries)

    """
    New suggestions might appear given a schema, depending on the RDBMS.
    """

    async def prepare(self, schema: domain.Schema) -> list[domain.Suggestion]:
        return []

    """
    New actions might appear given a query, depending on the RDBMS.
    """

    async def analyze(self, query: domain.Query) -> list[domain.Action]:
        pass

    """
    Should execute all the actions for a given suggestion, finding the best possible combination.
    The final result can contain between one (1) and N actions, being N the number of suggestions provided.
    The result message must also explain the reason for the actions selection.
    """

    async def execute(self, suggestions: [domain.Suggestion], schema: domain.Schema) -> analyzer.Node:
        cmds: list[analyzer.Command] = []
        for suggestion in suggestions:
            if suggestion.action.type_ == domain.ActionType.INDEX.value:
                cmds.append(_commands.Index(suggestion=suggestion, conn=self._pool, queries=self._queries))
            else:
                continue

        return await self._analyzer.generate(actions=cmds)
