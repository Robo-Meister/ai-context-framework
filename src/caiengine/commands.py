from __future__ import annotations

from enum import Enum


class COMMAND(str, Enum):
    """Marketing-aware command primitives exposed to connectors."""

    SEND_EMAIL = "send_email"
    SCHEDULE_CALL = "schedule_call"
    UPDATE_CRM = "update_crm"
    ESCALATE = "escalate_to_human"
    NOOP = "noop"


__all__ = ["COMMAND"]
