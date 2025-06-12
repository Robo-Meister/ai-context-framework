from datetime import datetime, timedelta
from caiengine.core.time_decay_scorer import TimeDecayScorer


def test_time_decay_scorer():
    scorer = TimeDecayScorer(decay_rate=1.0)
    now = datetime.utcnow()
    fresh = {"score": 1.0, "timestamp": now}
    old = {"score": 1.0, "timestamp": now - timedelta(seconds=10)}
    assert scorer.score(fresh) > scorer.score(old)
