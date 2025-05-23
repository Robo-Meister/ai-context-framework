from typing import Dict, List, Any, NamedTuple

from common.types.ScopeRoleKey import ScopeRoleKey


class FusedContext(NamedTuple):
    scope_role_key: ScopeRoleKey
    aggregated_content: any  # e.g. text summary, vector embedding, etc.
    start_time: float
    end_time: float
    confidence: float