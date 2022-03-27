from dataclasses import dataclass

from domain.entities.query import Query


@dataclass
class Column:
    name: str
    type: str
    nullable: str


@dataclass
class Table:
    name: str
    columns: list[Column]


@dataclass
class Schema:
    tables: list[Table]
    queries: list[Query]
