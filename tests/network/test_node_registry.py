import unittest
import importlib.util
from pathlib import Path
import sys

# Import NodeRegistry without pulling in heavy dependencies
MODULE_PATH = Path(__file__).resolve().parents[2]

# Load RoboId first so the relative import in node_registry works
ROBOID_PATH = MODULE_PATH / "src" / "caiengine" / "network" / "roboid.py"
spec_roboid = importlib.util.spec_from_file_location("caiengine.network.roboid", ROBOID_PATH)
roboid_module = importlib.util.module_from_spec(spec_roboid)
spec_roboid.loader.exec_module(roboid_module)
sys.modules['caiengine.network.roboid'] = roboid_module

# Load NodeRegistry
NR_PATH = MODULE_PATH / "src" / "caiengine" / "network" / "node_registry.py"
spec = importlib.util.spec_from_file_location("caiengine.network.node_registry", NR_PATH)
node_registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(node_registry)
sys.modules['caiengine.network.node_registry'] = node_registry
NodeRegistry = node_registry.NodeRegistry
RoboId = roboid_module.RoboId


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

    def hget(self, key, field):
        return self.store.get(key, {}).get(field)


class TestNodeRegistry(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.registry = NodeRegistry(self.redis)

    def test_join_and_members(self):
        self.registry.join(
            "robot.control@A#1",
            "10.0.0.1",
            capabilities=["camera"],
            drivers=["driver.camera"],
            apps=["nav"],
        )
        self.registry.join("robot.control@B#1", "10.0.0.2")
        # Join using RoboId instance
        rid = RoboId.parse("robot.virtual@wirtualny#42")
        self.registry.join(
            rid,
            "10.0.0.9",
            capabilities=["virtual"],
            meta={"zone": "lab"},
        )
        members = self.registry.members()
        self.assertEqual(members["robot.control@A#1"]["address"], "10.0.0.1")
        self.assertIn("camera", members["robot.control@A#1"]["capabilities"])
        self.assertIn("driver.camera", members["robot.control@A#1"].get("drivers", []))
        self.assertIn("nav", members["robot.control@A#1"]["apps"])
        self.assertEqual(members["robot.control@B#1"]["address"], "10.0.0.2")
        self.assertEqual(members[str(rid)]["address"], "10.0.0.9")
        self.assertEqual(members[str(rid)]["meta"].get("zone"), "lab")

    def test_leave(self):
        self.registry.join("robot.control@A#1", "10.0.0.1")
        self.registry.leave("robot.control@A#1")
        self.assertNotIn("robot.control@A#1", self.registry.members())

    def test_find_filters(self):
        self.registry.join("robot.control@A#1", "10.0.0.1")
        self.registry.join("robot.control@B#1", "10.0.0.2")
        self.registry.join(
            "robot.worker@A#1",
            "10.0.0.3",
            capabilities=["arm"],
            apps=["lift"],
        )

        by_role = self.registry.find(role="control")
        self.assertEqual(set(by_role.keys()), {"robot.control@A#1", "robot.control@B#1"})

        by_place = self.registry.find(place="A")
        self.assertEqual(set(by_place.keys()), {"robot.control@A#1", "robot.worker@A#1"})

        by_capability = self.registry.find(capability="arm")
        self.assertEqual(list(by_capability.keys()), ["robot.worker@A#1"])

        by_app = self.registry.find(app="lift")
        self.assertEqual(list(by_app.keys()), ["robot.worker@A#1"])

    def test_find_by_driver(self):
        self.registry.join(
            "robot.control@A#1",
            "10.0.0.1",
            capabilities=["camera"],
            drivers=["driver.camera"],
        )
        self.registry.join(
            "robot.worker@A#1",
            "10.0.0.2",
            capabilities=["arm"],
            drivers=["driver.arm"],
        )

        matches = self.registry.find(driver="driver.camera")
        self.assertEqual(list(matches.keys()), ["robot.control@A#1"])


if __name__ == "__main__":
    unittest.main()

