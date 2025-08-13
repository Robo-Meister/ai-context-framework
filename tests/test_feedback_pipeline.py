import unittest
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch.nn")

from caiengine.pipelines.feedback_pipeline import FeedbackPipeline
from caiengine.parser.log_parser import LogParser
from caiengine.core.learning.learning_manager import LearningManager
from caiengine.providers.mock_context_provider import MockContextProvider
from caiengine.interfaces.context_provider import ContextProvider


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


    def test_feedback_pipeline_randomized_batch(self):
        provider = Provider()
        log_parser = LogParser()
        manager = LearningManager(input_size=4, parser=log_parser)
        pipeline = FeedbackPipeline(provider, manager, learning_manager=manager)

        data_batch = [
            {
                "id": i,
                "roles": ["editor"],
                "timestamp": provider.get_context()[0]["timestamp"],
                "situations": [f"deal{i}"],
                "content": f"Edit of deal{i}",
                "context": {"deal": str(i)},
                "confidence": 0.9,
            }
            for i in range(50)
        ]
        candidates = [
            {"category": f"deal{i}", "context": {"deal": str(i)}, "base_weight": 1.0}
            for i in range(50)
        ]

        results = pipeline.run(data_batch, candidates)
        self.assertGreater(len(results), 0)
        self.assertTrue(all("prediction" in r for r in results))

        feedback = [(entry["content"], 1.0) for entry in data_batch[:5]]
        updated = pipeline.run([], [], feedback=feedback)
        self.assertIsInstance(updated, list)

if __name__ == "__main__":
    unittest.main()
