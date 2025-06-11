from datetime import datetime
import math
from interfaces.context_scorer import ContextScorer


class TimeDecayScorer(ContextScorer):
    """Score items with exponential time decay applied to a base score."""

    def __init__(self, base_score_key: str = "score", decay_rate: float = 0.01):
        self.base_score_key = base_score_key
        self.decay_rate = decay_rate

    def score(self, item: dict) -> float:
        base = float(item.get(self.base_score_key, 0.0))
        ts = item.get("timestamp")
        if not isinstance(ts, datetime):
            return base
        age_sec = (datetime.utcnow() - ts).total_seconds()
        weight = math.exp(-self.decay_rate * age_sec)
        return base * weight
