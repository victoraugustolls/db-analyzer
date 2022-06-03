import typing as t

from domain.entities.suggestion import Suggestion


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

    def suggestion(self) -> Suggestion:
        pass
