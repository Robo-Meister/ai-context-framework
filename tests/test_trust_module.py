import unittest

from core.trust_module import TrustModule


class TestTrustModule(unittest.TestCase):
    def setUp(self):
        self.weights = {
            "role": 0.4,
            "location": 0.2,
            "time": 0.1,
            "device": 0.15,
            "action": 0.15,
        }
        self.tm = TrustModule(weights=self.weights, distance_method="cosine")

    def test_base_trust_score(self):
        ctx = {
            "role": True,
            "location": True,
            "time": False,
            "device": True,
            "action": False,
        }
        trust = self.tm.calculate_trust(ctx)
        expected = (0.4 + 0.2 + 0.15) / sum(self.weights.values())
        self.assertAlmostEqual(trust, expected, places=5)

    def test_base_trust_with_required_layers(self):
        ctx = {
            "role": True,
            "location": False,
            "time": False,
            "device": True,
            "action": False,
        }
        trust = self.tm.calculate_trust(ctx, required_layers=["location"])
        # Should subtract location weight from present_score
        expected = (0.4 + 0.15 - 0.2) / sum(self.weights.values())
        self.assertAlmostEqual(trust, max(0.0, expected), places=5)

    def test_cosine_similarity(self):
        ctx1 = {"a": 1, "b": 0, "c": 1}
        ctx2 = {"a": 1, "b": 1, "c": 0}
        similarity = self.tm.compare_contexts(ctx1, ctx2)
        self.assertGreater(similarity, 0.0)
        self.assertLess(similarity, 1.0)

    def test_add_and_compare_memory(self):
        mem_context = {"role": 0.9, "location": 0.8, "time": 0.0, "device": 0.75, "action": 0.1}
        self.tm.add_to_memory(mem_context)

        ctx = {"role": 0.85, "location": 0.75, "time": 0.1, "device": 0.7, "action": 0.05}
        max_sim = self.tm.get_max_similarity(ctx)
        self.assertGreater(max_sim, 0.9)  # Should be very close

    def test_combined_trust(self):
        self.tm.add_to_memory({"role": 0.95, "location": 0.85, "time": 0.1, "device": 0.8, "action": 0.05})

        ctx_presence = {"role": True, "location": True, "time": False, "device": True, "action": False}
        ctx_scores = {"role": 0.9, "location": 0.8, "time": 0.0, "device": 0.75, "action": 0.0}

        trust = self.tm.compute_trust_with_memory(ctx_presence, ctx_scores)
        base = self.tm.calculate_trust(ctx_presence)
        self.assertAlmostEqual(trust, base * self.tm.get_max_similarity(ctx_scores), places=5)

if __name__ == "__main__":
    unittest.main()
