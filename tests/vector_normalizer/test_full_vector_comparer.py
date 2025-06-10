import unittest

from core.vector_normalizer.full_vector_comparer import FullVectorComparer


class TestFullVectorComparer(unittest.TestCase):
    def setUp(self):
        self.comparer = FullVectorComparer()
        self.ctx1 = {
            "time": "morning",
            "space": "around the house",
            "role": "user",
            "label": "task",
            "mood": "neutral",
            "network": "node123",
        }
        self.ctx2 = {
            "time": "afternoon",
            "space": "at office",
            "role": "user",
            "label": "task",
            "mood": "neutral",
            "network": "node123",
        }

    def test_compare(self):
        sim = self.comparer.compare(self.ctx1, self.ctx2)
        self.assertTrue(0.0 <= sim <= 1.0)

    def test_compare_batch(self):
        results = self.comparer.compare_batch([self.ctx1, self.ctx2])
        self.assertIn((0, 1), results)
        self.assertTrue(0.0 <= results[(0, 1)] <= 1.0)


if __name__ == "__main__":
    unittest.main()
