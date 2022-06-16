import dataclasses

from .query import Query


@dataclasses.dataclass
class Column:
    name: str
    type: str
    nullable: str


@dataclasses.dataclass
class Table:
    name: str
    columns: list[Column]


@dataclasses.dataclass
class Schema:
    tables: list[Table]
    queries: list[Query]
