import config
import querydb

from .executor import Executor
from executor.postgresql import PostgreSQL


async def new(rdbms: str, dsn: config.DSN, queries: querydb.QueryDB) -> Executor:
    match rdbms:
        case "postgres":
            return await PostgreSQL.create(dsn=dsn, queries=queries)
        case _:
            raise Exception("invalid rdbms")
