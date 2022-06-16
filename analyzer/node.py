import dataclasses
import typing as t
import uuid

from .command import Command


@dataclasses.dataclass
class Node:
    command: Command
    parent: t.Optional["Node"]
    children: list["Node"] = dataclasses.field(default_factory=list)
    uid: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)

    command_gain: float = 0
    command_cost: float = 0
    command_queries_gain: dict[str, float] = dataclasses.field(default_factory=dict)
    recommended: bool = False

    def add_child(self, child: "Node") -> None:
        self.children.append(child)

    @property
    def name(self) -> str:
        return self.command.name()

    @property
    def delta(self) -> float:
        delta = self.command_gain - self.command_cost
        if self.parent is None:
            return delta

        return self.parent.delta + delta
