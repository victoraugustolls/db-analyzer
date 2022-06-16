from collections import deque

import asyncpg

import analyzer
import config
import domain
from . import inserts


class Store:
    _pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def create(cls, dsn: config.DSN) -> "Store":
        pool: asyncpg.Pool = await asyncpg.create_pool(
            dsn=f"postgresql://{dsn.user}:{dsn.password}@{dsn.host}:{dsn.port}/{dsn.database}?search_path=masters",
        )

        return cls(pool=pool)

    async def save(self, queries: list[domain.Query], node: analyzer.Node) -> None:
        queries = [self.__query_to_tuple(q) for q in queries]

        actions_map: dict[str, tuple] = {}

        nodes: list[tuple] = []
        results: list[tuple] = []

        for child in node.children:
            child.parent = None

        to_crawl = deque(node.children)
        while to_crawl:
            current = to_crawl.popleft()
            nodes.append(self.__node_to_tuple(current))
            results.extend(self.__node_to_result_tuple(current))
            to_crawl.extend(current.children)

            action = current.command.suggestion().action
            actions_map[action.name] = self.__action_to_tuple(action)

        actions: list[tuple] = list(actions_map.values())

        print("Queries Total:", len(queries))
        print("Actions Total:", len(actions))
        print("Nodes Total:", len(nodes))
        print("Results Total:", len(results))

        conn: asyncpg.Connection = await self._pool.acquire()
        async with conn.transaction():
            await conn.execute("SET CONSTRAINTS masters.node_parent_fkey DEFERRED;")
            await conn.execute("TRUNCATE node_query_result, node, action, query;")
            await conn.executemany(inserts.query, queries)
            await conn.executemany(inserts.action, actions)
            await conn.executemany(inserts.node, nodes)
            await conn.executemany(inserts.results, results)

    @staticmethod
    def __query_to_tuple(q: domain.Query) -> tuple:
        return q.id, q.raw, None, f"'{q.plan.raw}'", q.runs, q.plan.cost

    @staticmethod
    def __action_to_tuple(a: domain.Action) -> tuple:
        return a.type_, a.name, a.command

    @staticmethod
    def __node_to_tuple(n: analyzer.Node) -> tuple:
        return (
            n.uid,
            n.command.suggestion().action.name,
            n.parent.uid if n.parent else None,
            n.command_gain,
            n.command_cost,
            n.recommended
        )

    @staticmethod
    def __node_to_result_tuple(n: analyzer.Node) -> list[tuple]:
        return [
            (
                n.uid,
                k,
                v
            )
            for k, v in n.command_queries_gain.items()
        ]
