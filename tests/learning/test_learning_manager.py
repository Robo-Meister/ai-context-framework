import pytest

from core.learning.learning_manager import LearningManager
from parser.log_parser import LogParser

sample_logs = [
    "2025-05-21T09:15:23 ERROR Admin failed login attempt on server1",
    "2025-05-21T09:20:00 INFO User connected to database",
    "2025-05-21T09:45:10 WARN Service timeout on network interface",
    "2025-05-22T14:00:00 DEBUG Unknown process started",
]

class TestLearningManager:
    def test_learning_manager_train_predict(self):
        log_parser = LogParser()
        manager = LearningManager(input_size=4, parser=log_parser)

        # Simulate training on logs
        for _ in range(50):
            for log in sample_logs:
                loss = manager.learn_from_log(log)
                assert loss >= 0  # loss should be non-negative

        # Ensure model learned something useful (trust scores converge)
        scores = []
        for log in sample_logs:
            score = manager.predict_from_log(log)
            if hasattr(score, 'item'):
                score = score.item()
            scores.append(score)
            assert 0.0 <= score <= 1.0  # trust score should be within bounds

        assert len(set(round(s, 2) for s in scores)) > 1, "Model didn't learn distinctions"


    def test_learning_manager_feedback_shift(self):
        log_parser = LogParser()
        manager = LearningManager(input_size=4, parser=log_parser)

        high_trust_log = "2025-05-21T09:20:00 INFO User connected to database"
        low_trust_log = "2025-05-21T09:15:23 ERROR Admin failed login attempt on server1"

        for _ in range(50):
            manager.learn_from_log(high_trust_log, y_true=1.0)
            manager.learn_from_log(low_trust_log, y_true=0.0)

        high_score = manager.predict_from_log(high_trust_log)
        low_score = manager.predict_from_log(low_trust_log)

        assert high_score > low_score, "Model failed to learn trust distinction"

