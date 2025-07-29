import unittest
import importlib.util
from pathlib import Path

# Import RoboId without triggering heavy package imports
MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "caiengine" / "network" / "roboid.py"
spec = importlib.util.spec_from_file_location("roboid", MODULE_PATH)
roboid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roboid)
RoboId = roboid.RoboId


class TestRoboId(unittest.TestCase):
    def test_parse_and_format(self):
        addr = "robot.transport@magazynA/mesh01#003"
        rid = RoboId.parse(addr)
        self.assertEqual(rid.node_type, "robot")
        self.assertEqual(rid.role, "transport")
        self.assertEqual(rid.place, "magazynA/mesh01")
        self.assertEqual(rid.instance, "003")
        self.assertEqual(str(rid), addr)

    def test_compare(self):
        a = RoboId.parse("robot.transport@A#1")
        b = RoboId.parse("robot.transport@B#1")
        result = a.compare(b)
        self.assertLess(result["similarity"], 1.0)
        self.assertIn("place", result["differences"])


if __name__ == "__main__":
    unittest.main()
