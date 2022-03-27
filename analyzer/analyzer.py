from .command import Command
from .node import Node
from .result import Result


class _NoopCommand(Command):
    async def apply(self) -> tuple[int, int]:
        return 0, 0

    async def rollback(self) -> None:
        return None


class Analyzer:
    _leaves: list[Node]

    def __init__(self):
        self._leaves = []

    async def generate(self, actions: list[Command]) -> Result:
        initial_node = Node(command=_NoopCommand(), parent=None)
        await self._mount(node=initial_node, actions=actions)

        # Order the leaves in descending order by delta.
        # This means that leaves with higher cost reductions comes first on the list.
        # self._leaves.sort(key=lambda x: (int(x.gain), -x.cost), reverse=True)
        self._leaves.sort(key=lambda x: int(x.delta), reverse=True)

        result = Result()
        for leaf in self._leaves:
            tree: list[Node] = []
            current = leaf
            while current.parent is not None:
                tree.append(current)
                current = current.parent

            # Reverse the tree to show the actions in the order they should be applied.
            tree.reverse()
            result.nodes.append(tree)

        return result

    async def _mount(self, node: Node, actions: list[Command]) -> Node:
        cumulative_gain = 0

        for index, action in enumerate(actions):
            queries_gain, gain, cost = await action.apply()
            cumulative_gain += gain

            # If gain > 0, then there was a reduction on total cost.
            if gain > 0:
                new_gain = node.gain + gain
                new_cost = node.cost + cost
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
                        queries_gain=node.queries_gain,
                        gain=new_gain,
                        cost=new_cost,
                        parent=node,
                    ),
                    actions=new_actions,
                )
                node.add_child(child=new_node)

            # If the cost was higher than the gains, consider the current node as a leaf:
            if cost > gain:
                self._leaves.append(node)

            # Rollback the executed action.
            await action.rollback()

        # If there were no gains on this node, there can be two causes:
        #   1. There were no more actions to perform -> it's a leaf
        #   2. There were no actions that resulted in a cost reduction -> it's a leaf
        if cumulative_gain == 0:
            self._leaves.append(node)

        return node
