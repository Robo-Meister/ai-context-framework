import unittest
from datetime import datetime, timedelta

from caiengine.interfaces.context_provider import ContextProvider
from caiengine.pipelines.sensor_pipeline import SensorPipeline


class Provider(ContextProvider):
    def __init__(self):
        super().__init__()


class TestSensorPipeline(unittest.TestCase):
    def test_basic_sensor_flow(self):
        provider = Provider()
        pipeline = SensorPipeline(provider)

        now = datetime.utcnow()
        data_batch = [
            {
                "timestamp": now,
                "context": {
                    "role": "sensor",
                    "environment": {"camera": "cam1", "temperature": 25},
                },
                "content": "cam1 snapshot",
            },
            {
                "timestamp": now + timedelta(seconds=1),
                "context": {
                    "role": "sensor",
                    "environment": {"camera": "cam1", "temperature": 25},
                },
                "content": "cam1 snapshot",
            },
        ]

        candidates = [
            {
                "category": "env",
                "context": {
                    "role": "sensor",
                    "environment": {"camera": "cam1", "temperature": 25},
                },
                "base_weight": 1.0,
            }
        ]

        result = pipeline.run(data_batch, candidates)
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 1)
        fused = next(iter(result.values()))
        self.assertEqual(fused["count"], 1)


if __name__ == "__main__":
    unittest.main()
