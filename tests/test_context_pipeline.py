import unittest

from pipelines.context_pipeline import ContextPipeline
from providers.mock_context_provider import MockContextProvider

class TestContextPipeline(unittest.TestCase):
    def test_context_pipeline(self):
        mock_provider = MockContextProvider()
        # pipeline = ContextPipeline(
        #     context_provider=mock_provider,
        #     categorizer=Categorizer(mock_provider),
        #     deduplicator=FuzzyDeduplicator(time_threshold_sec=300, fuzzy_threshold=0.7),
        #     fuser=Fuser()
        # )
        pipeline = ContextPipeline(context_provider=mock_provider)

        data_batch = []  # or some sample data
        candidates = []  # or some sample candidates
        result = pipeline.run(data_batch, candidates)
        # Simple output to verify
        print("\n=== Final Fused Result ===")
        for key, val in result.items():
            print(f"\nGroup {key}:")
            print(f"- Start: {val['start_time']}")
            print(f"- End: {val['end_time']}")
            print(f"- Confidence: {val['avg_confidence']:.2f}")
            print(f"- Content: {val['aggregated_content']}")
            print(f"- Count: {val['count']}")

        # Assertions
        assert isinstance(result, dict)
        assert all(isinstance(k, tuple) and isinstance(v, dict) for k, v in result.items())
        assert all("aggregated_content" in v for v in result.values())
        print("\n✅ All tests passed!")
