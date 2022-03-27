import asyncio
import json

import uvloop

from config import settings
from domain.entities.action import Action
from domain.entities.plan import Plan
from domain.entities.query import Query
from domain.entities.schema import Schema, Table, Column
from domain.entities.suggestion import Suggestion
from executors.postgresql import PostgreSQLExecutor
from vos import DSN


async def main():
    (schema, suggestions) = parse_input()

    executor = await PostgreSQLExecutor.create(parse_dsn(settings.executor, settings.password))

    new_suggestions = await executor.prepare(schema=schema)

    suggestions.extend(new_suggestions)

    result = await executor.execute(suggestions, schema)
    for i, tree in enumerate(result.nodes):
        print(f"Result #{i} - Total gains: {tree[len(tree)-1].gain} / Total cost: {tree[len(tree)-1].cost} / Delta: {tree[len(tree)-1].delta}")
        for j, node in enumerate(tree):
            print(f"\t- Action #{j}")
            print(f"\t\t{node.description}")


def parse_input() -> tuple[Schema, list[Suggestion]]:
    with open("../flagr.json") as file:
        data = json.load(file)

    schema = Schema(
        tables=[Table(
            name=table["name"],
            columns=[Column(**column) for column in table["columns"]]
        ) for table in data["schema"]["tables"]],
        queries=[Query(
            id=query["id"],
            raw=query["raw"],
            runs=query["runs"],
            plan=Plan(**query["plan"]),
        ) for query in data["schema"]["queries"]]
    )

    def find_query(uid: str) -> Query:
        for query in schema.queries:
            if query.id == uid:
                return query

        raise Exception("missing query definition for id:", uid)

    suggestions = [
        Suggestion(
            action=Action(
                name=suggestion["action"]["name"],
                type_=suggestion["action"]["type"],
                command=suggestion["action"]["command"],
            ),
            queries=[find_query(query) for query in suggestion["queries"]]
        )
        for suggestion in data["suggestions"]
    ]

    return schema, suggestions


def parse_dsn(config, password) -> DSN:
    return DSN(
        user=config.user,
        password=password,
        host=config.host,
        port=config.port,
        database=config.database,
    )


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
