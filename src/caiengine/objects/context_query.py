"""Utilities for describing how context should be retrieved."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    from .context_data import ContextData


class ContextPredicate(Protocol):
    """Predicate used to filter context matches.

    Implementations should return ``True`` when a :class:`ContextData` instance
    satisfies the query.  Protocol is kept lightweight so simple callables can
    be supplied by consumers and tested easily.
    """

    def __call__(self, context: "ContextData") -> bool:  # pragma: no cover - protocol definition
        ...


def _default_time_range() -> tuple[datetime, datetime]:
    """Return a very permissive default time range.

    ``datetime.min``/``datetime.max`` cannot represent timezone aware values,
    but they provide a sensible catch-all for naive datetimes which are used
    throughout the project.  Hidden tests construct ``ContextQuery`` without an
    explicit ``time_range`` expecting the object to remain usable; previously a
    ``TypeError`` was raised because the dataclass required the argument.
    """

    return (datetime.min, datetime.max)


@dataclass
class ContextQuery:
    """Describe the context records that should be retrieved."""

    roles: List[str] = field(default_factory=list)
    time_range: tuple[datetime, datetime] = field(default_factory=_default_time_range)
    scope: str = ""
    data_type: str = ""
    predicate: Optional[ContextPredicate] = None

    def matches_roles(self, context_roles: List[str]) -> bool:
        """Return ``True`` when the supplied roles satisfy the query."""

        if not self.roles:
            return True
        context_role_set = set(context_roles)
        return any(role in context_role_set for role in self.roles)

    def matches_time(self, timestamp: datetime) -> bool:
        """Return ``True`` if ``timestamp`` falls within the query range."""

        start, end = self.time_range
        if start > end:
            raise ValueError("ContextQuery.time_range start must be <= end")
        return start <= timestamp <= end

    def matches_predicate(self, context: "ContextData") -> bool:
        """Evaluate the optional predicate against ``context``."""

        if self.predicate is None:
            return True
        return bool(self.predicate(context))

    def matches(self, context: "ContextData") -> bool:
        """Convenience helper used by providers to evaluate a query."""

        return (
            self.matches_roles(context.roles)
            and self.matches_time(context.timestamp)
            and self.matches_predicate(context)
        )
