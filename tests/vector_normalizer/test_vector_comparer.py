import unittest

from core.vector_normalizer.vector_comparer import VectorComparer


class TestVectorComparer(unittest.TestCase):
    def setUp(self):
        self.vec1 = [0.2, 0.1, 0.2, 0.5, 0, 1, 0, 0.1, 0.3]
        self.vec2 = [0.6, 0.5, 0.6, 0.5, 0, 1, 0, 0.5, 0.3]
        self.weights = [1.5, 1, 1, 1.3, 1.2, 1.2, 1.2, 0.8, 1.0]
        self.comparer = VectorComparer(weights=self.weights)

    def test_cosine_similarity(self):
        sim = self.comparer.cosine_similarity(self.vec1, self.vec2)
        self.assertGreaterEqual(sim, 0.0)
        self.assertLessEqual(sim, 1.0)

    def test_euclidean_distance(self):
        dist = self.comparer.euclidean_distance(self.vec1, self.vec2)
        self.assertGreater(dist, 0.0)

    def test_zero_vector_similarity(self):
        zero_vec = [0.0] * 9
        sim = self.comparer.cosine_similarity(self.vec1, zero_vec)
        self.assertEqual(sim, 0.0)
