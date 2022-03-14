from dataclasses import dataclass, field

from .node import Node


@dataclass
class Result:
    nodes: list[list[Node]] = field(default_factory=list)
