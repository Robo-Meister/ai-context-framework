import unittest
from datetime import datetime, timedelta

from caiengine.pipelines.question_pipeline import QuestionPipeline
from caiengine.providers.memory_context_provider import MemoryContextProvider
from caiengine.interfaces.inference_engine import AIInferenceEngine
from caiengine.objects.context_query import ContextQuery


class Engine(AIInferenceEngine):
    def predict(self, input_data):
        return {"echo": input_data}


class TestQuestionPipeline(unittest.TestCase):
    def test_question_pipeline(self):
        provider = MemoryContextProvider()
        now = datetime.utcnow()
        provider.ingest_context(
            {"time": "morning", "space": "around the house", "role": "user", "label": "task"},
            timestamp=now,
            metadata={"content": "first"},
        )
        provider.ingest_context(
            {"time": "afternoon", "space": "at office", "role": "user", "label": "task"},
            timestamp=now + timedelta(hours=1),
            metadata={"content": "second"},
        )

        query = ContextQuery(roles=[], time_range=(now - timedelta(seconds=1), now + timedelta(hours=2)), scope="", data_type="")
        pipeline = QuestionPipeline(provider, Engine())
        result = pipeline.ask("How are you?", query, context={"time": "morning", "space": "around the house", "role": "user", "label": "task"})
        self.assertIn("answer", result)
        self.assertIn("fused", result)


if __name__ == "__main__":
    unittest.main()
