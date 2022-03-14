from dataclasses import dataclass

from .query import Query
from .action import Action


@dataclass
class Suggestion:
    action: Action
    queries: list[Query]

