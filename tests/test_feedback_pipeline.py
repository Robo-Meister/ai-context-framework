import unittest
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch.nn")

from pipelines.feedback_pipeline import FeedbackPipeline
from parser.log_parser import LogParser
from core.learning.learning_manager import LearningManager
from providers.mock_context_provider import MockContextProvider
from interfaces.context_provider import ContextProvider


class Provider(MockContextProvider, ContextProvider):
    def __init__(self):
        ContextProvider.__init__(self)


class TestFeedbackPipeline(unittest.TestCase):
    def test_feedback_pipeline_basic(self):
        provider = Provider()
        log_parser = LogParser()
        manager = LearningManager(input_size=4, parser=log_parser)
        pipeline = FeedbackPipeline(provider, manager, learning_manager=manager)

        data_batch = provider.get_context()
        candidates = [
            {"category": "deal1", "context": {"deal": "1"}, "base_weight": 1.0},
            {"category": "deal2", "context": {"deal": "2"}, "base_weight": 1.0},
        ]

        results = pipeline.run(data_batch, candidates)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn("prediction", results[0])

        feedback = [(data_batch[0]["content"], 1.0)]
        updated = pipeline.run([], [], feedback=feedback)
        self.assertIsInstance(updated, list)


if __name__ == "__main__":
    unittest.main()
