from dataclasses import dataclass

from domain.entities.action import Action
from domain.entities.query import Query


@dataclass
class ActionResult:
    action: Action
    new_cost: int
    old_cost: int
    message: str

    @property
    def delta(self) -> int:
        return self.old_cost - self.new_cost


@dataclass
class SuggestionResult:
    actions: list[ActionResult]
    query: list[Query]
    message: str
