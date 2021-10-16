import enum
from dataclasses import dataclass


class ActionType(enum.Enum):
    INDEX = "index"
    MATERIALIZED_VIEW = "materialized_view"

    # PostgreSQL only
    COLUMN_TETRIS = "column_tetris"


@dataclass
class Action:
    name: str
    type_: str
    command: str
