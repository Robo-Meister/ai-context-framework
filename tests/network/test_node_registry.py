import unittest
import importlib.util
from pathlib import Path

# Import NodeRegistry without pulling in heavy dependencies
MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "caiengine" / "network" / "node_registry.py"
spec = importlib.util.spec_from_file_location("node_registry", MODULE_PATH)
node_registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(node_registry)
NodeRegistry = node_registry.NodeRegistry


class FakeRedis:
    def __init__(self):
        self.store = {}

    def hset(self, key, field, value):
        self.store.setdefault(key, {})[field] = value

    def hdel(self, key, field):
        if key in self.store:
            self.store[key].pop(field, None)

    def hgetall(self, key):
        return self.store.get(key, {}).copy()


class TestNodeRegistry(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.registry = NodeRegistry(self.redis)

    def test_join_and_members(self):
        self.registry.join("robot.control@A#1", "10.0.0.1")
        self.registry.join("robot.control@B#1", "10.0.0.2")
        members = self.registry.members()
        self.assertEqual(members["robot.control@A#1"], "10.0.0.1")
        self.assertEqual(members["robot.control@B#1"], "10.0.0.2")

    def test_leave(self):
        self.registry.join("robot.control@A#1", "10.0.0.1")
        self.registry.leave("robot.control@A#1")
        self.assertNotIn("robot.control@A#1", self.registry.members())


if __name__ == "__main__":
    unittest.main()

