import typing as t

import analyzer
import domain


class Executor(t.Protocol):
    async def prepare(self, schema: domain.Schema) -> list[domain.Suggestion]:
        pass

    async def analyze(self, query: domain.Query) -> list[domain.Action]:
        pass

    async def execute(self, suggestions: [domain.Suggestion], schema: domain.Schema) -> analyzer.Node:
        pass
