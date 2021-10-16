from dataclasses import dataclass

from .query import Query
from .action import Action


@dataclass
class Suggestion:
    actions: list[Action]
    query: Query | None

