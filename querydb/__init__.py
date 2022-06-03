from dataclasses import dataclass

from domain.entities.query import Query


@dataclass
class QueryDB:
    _queries: dict[str, Query]

    def __init__(self, queries: list[Query]) -> None:
        self._queries = {
            query.id: query
            for query in queries
        }

    def replace(self, uid: str, query: Query) -> None:
        self._queries[uid] = query

    def with_table(self, table: str) -> list[Query]:
        return list(filter(lambda x: x.table == table, self._queries.values()))
