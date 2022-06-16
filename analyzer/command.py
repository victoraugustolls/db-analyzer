import typing as t

import domain


class Command(t.Protocol):
    # Apply returns a tuple, being:
    # - first is the associated gains per query
    # - second is the total gain
    # - third is the cost
    async def apply(self) -> tuple[dict[str, float], float, float]:
        pass

    async def rollback(self) -> None:
        pass

    def name(self) -> str:
        pass

    def description(self) -> str:
        pass

    def suggestion(self) -> domain.Suggestion:
        pass


class Noop(Command):
    def name(self) -> str:
        return "noop"

    async def apply(self) -> tuple[dict[str, float], float, float]:
        return {}, 0, 0

    async def rollback(self) -> None:
        return None
