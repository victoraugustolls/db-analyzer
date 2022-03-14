import typing as t
from dataclasses import dataclass, field

from .command import Command


@dataclass
class Node:
    command: Command
    parent: t.Optional["Node"]
    children: list["Node"] = field(default_factory=list)
    gain: int = 0
    cost: int = 0

    def add_child(self, child: "Node") -> None:
        self.children.append(child)

    @property
    def delta(self) -> int:
        return self.gain - self.cost
