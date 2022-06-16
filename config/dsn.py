import dataclasses


@dataclasses.dataclass
class DSN:
    user: str
    password: str
    host: str
    port: int
    database: str
