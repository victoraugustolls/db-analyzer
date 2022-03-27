import typing as t


class Command(t.Protocol):
    # Apply returns a tuple, being:
    # - first is the associated gains per query
    # - second is the total gain
    # - third is the cost
    async def apply(self) -> tuple[dict[str, float], float, float]:
        pass

    async def rollback(self) -> None:
        pass

    def description(self) -> str:
        pass
