from typing import Dict, Any

from core.policy_evaluator import PolicyEvaluator
class SimplePolicyEvaluator(PolicyEvaluator):
    # def evaluate(self, context_item: Dict[str, Any]) -> bool:
    def evaluate(self, context_item: dict) -> bool:
        """
        Accepts items from allowed roles and within time bounds.
        """
        from datetime import datetime, timedelta

        allowed_roles = {"user", "client", "employee", "ai"}
        max_age = timedelta(hours=6)

        ts = context_item.get("timestamp", datetime.min)
        role = context_item.get("role", "")

        is_allowed = (
            role in allowed_roles and
            (datetime.utcnow() - ts) <= max_age
        )
        return is_allowed
