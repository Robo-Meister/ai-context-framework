import unittest
from caiengine.interfaces.context_provider import ContextProvider
from caiengine.core.categorizer import Categorizer

class TestSublayerSupport(unittest.TestCase):
    def test_trust_and_compare_with_sublayers(self):
        provider = ContextProvider()
        cat = Categorizer(provider)

        ctx = {
            "role": "admin",
            "environment": {
                "camera": "cam1",
                "temperature": 25,
            }
        }
        candidate = {
            "category": "env",
            "context": {
                "role": "admin",
                "environment": {
                    "camera": "cam1",
                    "temperature": 25,
                }
            },
            "base_weight": 1.0,
        }

        trust = provider.calculate_trust(ctx)
        self.assertGreater(trust, 0)

        score = cat.compare_layers(ctx, candidate["context"])
        self.assertEqual(score, 1.0)

if __name__ == "__main__":
    unittest.main()
