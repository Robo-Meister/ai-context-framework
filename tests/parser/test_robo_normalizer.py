import unittest
from parser.robo_connector_normalizer import RoboConnectorNormalizer

EXAMPLE1 = {
    "workflow_name": "scale_digital_product",
    "description": "Workflow to build infrastructure and scale the digital product to more clients efficiently.",
    "steps": [
        {"name": "Assess current infrastructure capacity", "action": "evaluate", "level": 1},
        {"name": "Optimize backend services", "action": "refactor", "level": 2}
    ]
}

EXAMPLE2 = {
    "type": "workflow",
    "name": "Vote for Changes",
    "description": "Organize tenant voting for changes like renovations or new rules.",
    "fields": ["topic", "description"],
    "steps": [
        {"name": "Propose Changes", "action": "Send Proposals", "level": 0},
        {"name": "Collect Votes", "action": "Record Votes", "level": 1}
    ]
}

class TestRoboConnectorNormalizer(unittest.TestCase):
    def setUp(self):
        self.norm = RoboConnectorNormalizer()

    def test_normalize_workflow_name(self):
        result = self.norm.normalize(EXAMPLE1)
        self.assertEqual(result["name"], "scale_digital_product")
        self.assertEqual(len(result["steps"]), 2)

    def test_normalize_generic(self):
        result = self.norm.normalize(EXAMPLE2)
        self.assertEqual(result["name"], "Vote for Changes")
        self.assertIn("fields", result)
        self.assertEqual(result["steps"][0]["name"], "Propose Changes")

if __name__ == "__main__":
    unittest.main()
