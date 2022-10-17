from .command import Command, Noop
from .node import Node


class Analyzer:
    _leaves: list[Node]
    _max_delta: float
    _recommended: Node

    _counter: int = 0
    _columns: dict[int, int] = {}

    def __init__(self):
        self._leaves = []
        self._max_delta = float("-inf")

    async def generate(self, actions: list[Command]) -> Node:
        node = Node(command=Noop(), parent=None)
        self._recommended = node
        await self._mount(node=node, actions=actions, row=0)

        current = self._recommended
        while current is not None:
            current.recommended = True
            current = current.parent

        return node

    async def _mount(self, node: Node, actions: list[Command], row: int) -> Node:
        row = row + 1
        column = self._columns.get(row)
        if column is None:
            column = 0

        for index, action in enumerate(actions):
            queries_gain, gain, cost = await action.apply()
            self._counter += 1
            if self._counter % 10 == 0:
                print("Counter:", self._counter)
                print("Row:", row)
                print("Column:", column)
                print()

            if self._counter % 1000 == 0 and self._counter > 0:
                print("Row 1 column:", self._columns[1])
                print("Row 2 column:", self._columns[2])
                print()

            column = column + 1
            self._columns[row] = column

            if gain <= 0:
                await action.rollback()
                continue

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
                row=row,
            )

            if new_node.delta > self._max_delta:
                self._max_delta = new_node.delta
                self._recommended = new_node

            node.add_child(child=new_node)

            # Rollback the executed action.
            await action.rollback()

        self._columns[row] = column
        return node
