import unittest

from ContextAi.core.vector_normalizer.context_encoder import ContextEncoder


class TestContextEncoder(unittest.TestCase):
    def setUp(self):
        self.encoder = ContextEncoder()

    def test_full_context(self):
        context = {
            "time": "morning",
            "space": "around the house",
            "role": "user",
            "label": "task",
            "mood": "happy",
            "network": "node123"
        }
        vector = self.encoder.encode(context)
        self.assertEqual(len(vector), 9)
        self.assertAlmostEqual(vector[0], 0.2)  # morning
        self.assertEqual(vector[1:3], [0.1, 0.2])  # space
        self.assertEqual(vector[3], 0.5)  # role
        self.assertEqual(vector[4:7], [0, 1, 0])  # label
        self.assertEqual(vector[7], 0.1)  # mood
        self.assertGreaterEqual(vector[8], 0.0)  # hashed value
        self.assertLessEqual(vector[8], 1.0)

    def test_partial_context(self):
        context = {"space": "warehouse"}
        vector = self.encoder.encode(context)
        self.assertEqual(len(vector), 9)
        self.assertEqual(vector[0], 0.0)  # missing time
        self.assertEqual(vector[1:3], [0.8, 0.9])
        self.assertEqual(vector[3], 0.0)  # missing role
        self.assertEqual(vector[4:7], [0.0, 0.0, 0.0])  # missing label
        self.assertEqual(vector[7], 0.0)  # missing mood
        self.assertEqual(vector[8], 0.0)  # missing network
