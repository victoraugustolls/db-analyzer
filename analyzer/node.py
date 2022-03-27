import typing as t
from dataclasses import dataclass, field

from .command import Command


@dataclass
class Node:
    command: Command
    parent: t.Optional["Node"]
    children: list["Node"] = field(default_factory=list)
    gain: float = 0
    cost: float = 0
    queries_gain: dict[str, float] = field(default_factory=dict)
    command_gain: float = 0
    command_cost: float = 0
    command_queries_gain: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        for query, gain in self.command_queries_gain.items():
            current = self.queries_gain.get(query) or 0
            self.queries_gain[query] = current + gain

    def add_child(self, child: "Node") -> None:
        self.children.append(child)

    @property
    def delta(self) -> float:
        return self.gain - self.cost

    @property
    def description(self) -> str:
        query_gains = ""
        for query, gain in self.command_queries_gain.items():
            query_gains += f"\n\t\t\t- Query {query} had a gain of {gain}"

        return self.command.description() + f"\n\t\t\tGain: {self.command_gain} / Cost: {self.command_cost}" + query_gains
