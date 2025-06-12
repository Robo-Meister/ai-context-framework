from typing import Protocol, Callable, List
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class ContextQuery:
    roles: List[str]
    time_range: tuple[datetime, datetime]
    scope: str
    data_type: str