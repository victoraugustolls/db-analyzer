from dataclasses import dataclass, field

from .node import Node


@dataclass
class Result:
    nodes: list[list[Node]] = field(default_factory=list)


def fingerprint(n: list[Node]) -> str:
    s = "$$".join(list(
        map(
            lambda node: node.fingerprint(),
            sorted(n, key=lambda node: node.name)
        )
    ))

    return s
