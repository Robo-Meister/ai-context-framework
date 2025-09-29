import unittest
import importlib.util
from pathlib import Path
import sys

# Setup module paths
MODULE_PATH = Path(__file__).resolve().parents[2]

# Load RoboId
ROBOID_PATH = MODULE_PATH / "src" / "caiengine" / "network" / "roboid.py"
spec_roboid = importlib.util.spec_from_file_location("caiengine.network.roboid", ROBOID_PATH)
roboid_module = importlib.util.module_from_spec(spec_roboid)
spec_roboid.loader.exec_module(roboid_module)
sys.modules['caiengine.network.roboid'] = roboid_module
RoboId = roboid_module.RoboId

# Load NodeRegistry
NR_PATH = MODULE_PATH / "src" / "caiengine" / "network" / "node_registry.py"
spec_nr = importlib.util.spec_from_file_location("caiengine.network.node_registry", NR_PATH)
node_registry = importlib.util.module_from_spec(spec_nr)
spec_nr.loader.exec_module(node_registry)
sys.modules['caiengine.network.node_registry'] = node_registry
NodeRegistry = node_registry.NodeRegistry

# Load NodeManager
NM_PATH = MODULE_PATH / "src" / "caiengine" / "network" / "node_manager.py"
spec_nm = importlib.util.spec_from_file_location("caiengine.network.node_manager", NM_PATH)
node_manager = importlib.util.module_from_spec(spec_nm)
sys.modules['caiengine.network.node_manager'] = node_manager
spec_nm.loader.exec_module(node_manager)
NodeManager = node_manager.NodeManager
NodeInfo = node_manager.NodeInfo


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


class TestNodeManager(unittest.TestCase):
    def setUp(self):
        self.registry = NodeRegistry(FakeRedis())
        self.manager = NodeManager(self.registry)

    def test_register_and_get(self):
        self.manager.register(
            "robot.control@A#1",
            "10.0.0.1",
            capabilities=["camera", "compute"],
            drivers=["driver.camera"],
            apps=["nav"],
            metadata={"zone": "alpha"},
        )
        info = self.manager.get("robot.control@A#1")
        self.assertIsNotNone(info)
        assert isinstance(info, NodeInfo)
        self.assertEqual(info.address, "10.0.0.1")
        self.assertIn("camera", info.capabilities)
        self.assertIn("driver.camera", info.drivers)
        self.assertTrue(self.manager.has_app("robot.control@A#1", "nav"))
        self.assertEqual(info.metadata.get("zone"), "alpha")

        stored = self.registry.get("robot.control@A#1")
        assert stored is not None
        self.assertIn("camera", stored.get("capabilities", []))
        self.assertIn("driver.camera", stored.get("drivers", []))
        self.assertIn("nav", stored.get("apps", []))
        self.assertEqual(stored.get("meta", {}).get("zone"), "alpha")

    def test_find_by_capability(self):
        self.manager.register("robot.control@A#1", "10.0.0.1", capabilities=["camera"])
        self.manager.register("robot.worker@A#2", "10.0.0.2", capabilities=["arm"])
        matches = self.manager.find_by_capability("camera")
        self.assertEqual(set(matches.keys()), {"robot.control@A#1"})
        self.assertEqual(matches["robot.control@A#1"].address, "10.0.0.1")

    def test_add_app_updates_registry(self):
        self.manager.register("robot.control@A#1", "10.0.0.1", apps=["nav"])
        self.manager.add_app("robot.control@A#1", "vision")
        info = self.manager.get("robot.control@A#1")
        assert info is not None
        self.assertIn("vision", info.apps)

        stored = self.registry.get("robot.control@A#1")
        assert stored is not None
        self.assertIn("vision", stored.get("apps", []))

    def test_add_driver_updates_registry(self):
        self.manager.register("robot.control@A#1", "10.0.0.1")
        self.manager.add_driver("robot.control@A#1", "driver.camera")
        info = self.manager.get("robot.control@A#1")
        assert info is not None
        self.assertIn("driver.camera", info.drivers)

        stored = self.registry.get("robot.control@A#1")
        assert stored is not None
        self.assertIn("driver.camera", stored.get("drivers", []))

    def test_manager_loads_existing_registry(self):
        self.manager.register("robot.control@A#1", "10.0.0.1", capabilities=["camera"])
        # Recreate manager with same registry backend
        new_manager = NodeManager(self.registry)
        info = new_manager.get("robot.control@A#1")
        assert info is not None
        self.assertIn("camera", info.capabilities)


if __name__ == "__main__":
    unittest.main()
