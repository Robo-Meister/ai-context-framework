import unittest
from datetime import datetime, timedelta

from caiengine.pipelines.vector_pipeline import VectorPipeline
from caiengine.interfaces.context_provider import ContextProvider


class VectorProvider(ContextProvider):
    def __init__(self):
        super().__init__()
        base = datetime(2024, 1, 1, 12, 0)
        self._data = [
            {
                "id": 1,
                "roles": ["user"],
                "timestamp": base,
                "situations": ["s1"],
                "content": "v1",
                "context": {"deal": "1"},
                "vector": [0.1, 0.2, 0.3],
                "confidence": 0.9,
            },
            {
                "id": 2,
                "roles": ["user"],
                "timestamp": base + timedelta(seconds=2),
                "situations": ["s1"],
                "content": "v2",
                "context": {"deal": "1"},
                "vector": [0.1, 0.2, 0.31],
                "confidence": 0.8,
            },
        ]

    def get_context(self):
        return self._data


class TestVectorPipeline(unittest.TestCase):
    def test_vector_pipeline_runs(self):
        provider = VectorProvider()
        pipeline = VectorPipeline(provider, vector_dim=3)
        data_batch = provider.get_context()
        candidates = [
            {"category": "deal1", "context": {"deal": "1"}, "base_weight": 1.0},
        ]
        result = pipeline.run(data_batch, candidates)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
