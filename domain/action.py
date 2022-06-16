import dataclasses
import enum


class ActionType(enum.Enum):
    INDEX = "index"
    MATERIALIZED_VIEW = "materialized_view"

    # PostgreSQL only
    COLUMN_TETRIS = "column_tetris"


@dataclasses.dataclass
class Action:
    # name must be unique
    name: str
    type_: str
    command: str
