import typing as t


class Command(t.Protocol):
    # Apply returns a tuple of integers, being:
    # - first is the associated gains
    # - second is the cost
    async def apply(self) -> tuple[int, int]:
        pass

    async def rollback(self) -> None:
        pass

    def description(self) -> str:
        pass
