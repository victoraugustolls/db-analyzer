import dataclasses

import domain


@dataclasses.dataclass
class QueryDB:
    _queries: dict[str, domain.Query]

    def __init__(self, queries: list[domain.Query]) -> None:
        self._queries = {
            query.id: query
            for query in queries
        }

    def queries(self) -> list[domain.Query]:
        return list(self._queries.values())

    def replace(self, uid: str, query: domain.Query) -> None:
        self._queries[uid] = query

    def with_table(self, table: str) -> list[domain.Query]:
        return list(filter(lambda x: x.table == table, self._queries.values()))
