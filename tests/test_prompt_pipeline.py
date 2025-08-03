import unittest
from datetime import datetime, timedelta

from caiengine.pipelines.prompt_pipeline import PromptPipeline
from caiengine.providers.memory_context_provider import MemoryContextProvider
from caiengine.interfaces.inference_engine import AIInferenceEngine
from caiengine.objects.context_query import ContextQuery


class Engine(AIInferenceEngine):
    def predict(self, input_data):
        return {"echo": input_data}


class TestPromptPipeline(unittest.TestCase):
    def test_prompt_pipeline(self):
        provider = MemoryContextProvider()
        now = datetime.utcnow()
        provider.ingest_context(
            {"time": "morning", "space": "around the house", "role": "user", "label": "task"},
            timestamp=now,
            metadata={"content": "first"},
        )
        query = ContextQuery(
            roles=[],
            time_range=(now - timedelta(seconds=1), now + timedelta(seconds=1)),
            scope="",
            data_type="",
        )
        pipeline = PromptPipeline(provider, Engine())
        result = pipeline.process("user is happy at home in the morning", query)
        self.assertIn("result", result)
        self.assertIn("fused", result)
        self.assertIn("parsed", result)
        self.assertEqual(result["parsed"]["time"], "morning")


if __name__ == "__main__":
    unittest.main()
