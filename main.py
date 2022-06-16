import asyncio
import json

import uvloop

import config
import domain
import executors.postgresql as executors
import querydb
import store


async def main():
    (schema, suggestions) = parse_input()

    queries = querydb.QueryDB(queries=schema.queries)

    dsn = parse_dsn(config.settings.executor, config.settings.password)

    executor = await executors.PostgreSQLExecutor.create(dsn, queries)

    new_suggestions = await executor.prepare(schema=schema)

    suggestions.extend(new_suggestions)

    result = await executor.execute(suggestions, schema)

    st = await store.Store.create(dsn=dsn)
    await st.save(queries=schema.queries, node=result)


def parse_input() -> tuple[domain.Schema, list[domain.Suggestion]]:
    with open("flagr.json") as file:
        data = json.load(file)

    schema = domain.Schema(
        tables=[domain.Table(
            name=table["name"],
            columns=[domain.Column(**column) for column in table["columns"]]
        ) for table in data["schema"]["tables"]],
        queries=[domain.Query(
            id=query["id"],
            raw=query["raw"],
            runs=query["runs"],
            plan=domain.Plan(**query["plan"]),
        ) for query in data["schema"]["queries"]]
    )

    def find_query(uid: str) -> domain.Query:
        for query in schema.queries:
            if query.id == uid:
                return query

        raise Exception("missing query definition for id:", uid)

    suggestions = [
        domain.Suggestion(
            action=domain.Action(
                name=suggestion["action"]["name"],
                type_=suggestion["action"]["type"],
                command=suggestion["action"]["command"],
            ),
            queries=[find_query(query) for query in suggestion["queries"]]
        )
        for suggestion in data["suggestions"]
    ]

    return schema, suggestions


def parse_dsn(cfg, password) -> config.DSN:
    return config.DSN(
        user=cfg.user,
        password=password,
        host=cfg.host,
        port=cfg.port,
        database=cfg.database,
    )


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
