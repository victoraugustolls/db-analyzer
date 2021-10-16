from dataclasses import dataclass

from .plan import Plan


@dataclass
class Query:
    id: str
    raw: str
    plan: Plan
