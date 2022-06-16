from .command import Command, Noop
from .node import Node


class Analyzer:
    _leaves: list[Node]
    _max_delta: float
    _recommended: Node

    def __init__(self):
        self._leaves = []
        self._max_delta = float("-inf")

    async def generate(self, actions: list[Command]) -> Node:
        node = Node(command=Noop(), parent=None)
        await self._mount(node=node, actions=actions)

        current = self._recommended
        while current is not None:
            current.recommended = True
            current = current.parent

        return node

    async def _mount(self, node: Node, actions: list[Command]) -> Node:
        for index, action in enumerate(actions):
            queries_gain, gain, cost = await action.apply()

            # New actions list, excluding the current one that was executed.
            new_actions = actions.copy()
            new_actions.pop(index)

            # Recursively build the Node tree.
            new_node = await self._mount(
                node=Node(
                    command=action,
                    command_queries_gain=queries_gain,
                    command_gain=gain,
                    command_cost=cost,
                    parent=node,
                ),
                actions=new_actions,
            )

            if new_node.delta > self._max_delta:
                self._max_delta = new_node.delta
                self._recommended = new_node

            node.add_child(child=new_node)

            # Rollback the executed action.
            await action.rollback()

        return node
