from dataclasses import dataclass


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
