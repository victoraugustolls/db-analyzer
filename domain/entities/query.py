from dataclasses import dataclass, field
from enum import Enum

from .plan import Plan


class QueryType(Enum):
    INSERT = "INSERT"
    SELECT = "SELECT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class Query:
    id: str
    raw: str
    runs: int
    plan: Plan | None
    _type: QueryType = field(init=False)
    table: str = ""

    def __post_init__(self):
        self.raw = self.raw.strip()

        split = self.raw.split(" ", 1)
        if len(split) != 2:
            raise Exception("invalid sql query")

        self._type = QueryType(split[0].upper())
        if self._type == QueryType.SELECT:
            return

        index = 2
        if self._type == QueryType.UPDATE:
            index = 1

        split = self.raw.split(" ", index+1)
        if len(split) != index + 2:
            raise Exception("invalid sql query")

        self.table = split[index]
