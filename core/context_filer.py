from typing import List, Dict, Any

from interfaces.context_scorer import ContextScorer
from core.policy_evaluator import PolicyEvaluator


class ContextFilter:
    def __init__(self, scorer: ContextScorer, policy: PolicyEvaluator, threshold: float = 0.2):
        self.scorer = scorer
        self.policy = policy
        self.threshold = threshold

    def filter(self, context_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for item in context_items:
            allowed = self.policy.evaluate(item)
            score = self.scorer.score(item) if allowed else 0.0
            item["policy_allowed"] = allowed
            item["score"] = score
            if allowed and score >= self.threshold:
                results.append(item)
        return results
