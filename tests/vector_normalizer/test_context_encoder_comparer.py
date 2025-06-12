import unittest
from caiengine.core.vector_normalizer.context_encoder import ContextEncoder
from caiengine.core.vector_normalizer.vector_comparer import VectorComparer

class TestContextEncoderComparer(unittest.TestCase):
    def setUp(self):
        self.encoder = ContextEncoder()
        weights = [1.5, 1, 1, 1.3, 1.2, 1.2, 1.2, 0.8, 1.0]
        self.comparer = VectorComparer(weights=weights)

    def test_compare_similar_contexts(self):
        ctx1 = {
            "time": "morning", "space": "around the house", "role": "user",
            "label": "task", "mood": "neutral", "network": "node123"
        }
        ctx2 = {
            "time": "afternoon", "space": "at office", "role": "user",
            "label": "task", "mood": "neutral", "network": "node123"
        }
        vec1 = self.encoder.encode(ctx1)
        vec2 = self.encoder.encode(ctx2)

        cosine_sim = self.comparer.cosine_similarity(vec1, vec2)
        euclidean_dist = self.comparer.euclidean_distance(vec1, vec2)

        self.assertTrue(0.0 <= cosine_sim <= 1.0)
        self.assertGreater(euclidean_dist, 0)

