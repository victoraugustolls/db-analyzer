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

    results = []
    for suggestion in suggestions:
        results.append(await executor.execute(suggestion))

    for result in results:
        print(result.message)
        print()


def parse_input() -> tuple[Schema, list[Suggestion]]:
    with open("../input.json") as file:
        data = json.load(file)

    schema = Schema(tables=[
        Table(name=table["name"], columns=[
            Column(**column)
            for column in table["columns"]
        ])
        for table in data["schema"]["tables"]]
    )

    suggestions = [
        Suggestion(
            actions=[
                Action(name=action["name"], type_=action["type"], command=action["command"])
                for action in suggestion["actions"]
            ],
            query=Query(
                id=suggestion["query"]["id"],
                raw=suggestion["query"]["raw"],
                plan=Plan(**suggestion["query"]["plan"]),
            ),
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
