import unittest
from datetime import datetime

from caiengine.pipelines.configurable_pipeline import ConfigurablePipeline


class TestConfigurablePipeline(unittest.TestCase):
    def test_build_and_run_goal(self):
        cfg = {
            "provider": {"type": "memory"},
            "candidates": [
                {"category": "foo", "context": {"foo": "bar"}, "base_weight": 1.0}
            ],
            "policy": "simple",
            "trust_weights": {"foo": 1.0},
            "feedback": {"type": "goal", "goal_state": {"progress": 10}},
        }
        pipeline = ConfigurablePipeline.from_dict(cfg)
        now = datetime.utcnow()
        data_batch = [
            {
                "timestamp": now,
                "context": {"foo": "bar"},
                "roles": [],
                "situations": [],
                "role": "user",
                "content": "text",
                "confidence": 1.0,
            }
        ]
        result = pipeline.run(data_batch)
        self.assertEqual(len(result), 1)
        self.assertIn("goal_suggestion", result[0])


if __name__ == "__main__":
    unittest.main()
