import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import List

MODULE_PATH = Path(__file__).resolve().parents[2]
NETWORK_SRC = MODULE_PATH / "src" / "caiengine" / "network"
INTERFACE_SRC = MODULE_PATH / "src" / "caiengine" / "interfaces"


def _load(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


caiengine_module = types.ModuleType("caiengine")
caiengine_module.__path__ = [str(MODULE_PATH / "src" / "caiengine")]
sys.modules.setdefault("caiengine", caiengine_module)

network_package = types.ModuleType("caiengine.network")
network_package.__path__ = [str(NETWORK_SRC)]
sys.modules.setdefault("caiengine.network", network_package)
caiengine_module.network = network_package

interfaces_module = types.ModuleType("caiengine.interfaces")
interfaces_module.__path__ = [str(INTERFACE_SRC)]
sys.modules.setdefault("caiengine.interfaces", interfaces_module)
caiengine_module.interfaces = interfaces_module
network_interface_module = _load(
    "caiengine.interfaces.network_interface",
    INTERFACE_SRC / "network_interface.py",
)
interfaces_module.network_interface = network_interface_module

_load("caiengine.network.roboid", NETWORK_SRC / "roboid.py")
node_registry_module = _load("caiengine.network.node_registry", NETWORK_SRC / "node_registry.py")
node_manager_module = _load("caiengine.network.node_manager", NETWORK_SRC / "node_manager.py")
capability_registry_module = _load("caiengine.network.capability_registry", NETWORK_SRC / "capability_registry.py")
driver_resolver_module = _load("caiengine.network.driver_resolver", NETWORK_SRC / "driver_resolver.py")
dispatcher_module = _load("caiengine.network.dispatcher", NETWORK_SRC / "dispatcher.py")
observability_module = _load("caiengine.network.observability", NETWORK_SRC / "observability.py")

NodeRegistry = node_registry_module.NodeRegistry
NodeManager = node_manager_module.NodeManager
CapabilityRegistry = capability_registry_module.CapabilityRegistry
DriverResolver = driver_resolver_module.DriverResolver
MeshDispatcher = dispatcher_module.MeshDispatcher
DispatchMonitor = observability_module.DispatchMonitor
DispatchEvent = observability_module.DispatchEvent


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


class FakeNetwork:
    def __init__(self):
        self.sent: List = []

    def send(self, recipient_id: str, message: dict):
        self.sent.append((recipient_id, message))

    def broadcast(self, message: dict):  # pragma: no cover - not used
        self.sent.append(("broadcast", message))

    def receive(self):  # pragma: no cover - not needed
        return None

    def start_listening(self, _cb):  # pragma: no cover - not needed
        return None


class TestCapabilityRegistry(unittest.TestCase):
    def setUp(self):
        registry = NodeRegistry(FakeRedis())
        self.node_manager = NodeManager(registry)
        self.cap_registry = CapabilityRegistry(self.node_manager)

    def test_register_and_find(self):
        self.cap_registry.register(
            "robot.sensor@A#1",
            "10.0.0.1",
            capabilities=["lidar"],
            drivers=["driver.lidar"],
        )
        self.cap_registry.register(
            "robot.sensor@A#2",
            "10.0.0.2",
            capabilities=["lidar"],
        )

        record = self.cap_registry.get("robot.sensor@A#1")
        assert record is not None
        self.assertTrue(self.cap_registry.has_requirements("robot.sensor@A#1", capabilities=["lidar"]))
        self.assertTrue(self.cap_registry.has_requirements("robot.sensor@A#1", drivers=["driver.lidar"]))

        matches = self.cap_registry.find(capabilities=["lidar"], drivers=["driver.lidar"])
        self.assertEqual(list(matches.keys()), ["robot.sensor@A#1"])

    def test_mark_driver_available(self):
        self.cap_registry.register(
            "robot.sensor@A#1",
            "10.0.0.1",
            capabilities=["lidar"],
        )
        self.cap_registry.mark_driver_available("robot.sensor@A#1", "driver.lidar")
        self.assertTrue(self.cap_registry.has_driver("robot.sensor@A#1", "driver.lidar"))


class TestDriverResolver(unittest.TestCase):
    def setUp(self):
        registry = NodeRegistry(FakeRedis())
        manager = NodeManager(registry)
        self.cap_registry = CapabilityRegistry(manager)
        self.cap_registry.register(
            "robot.sensor@A#1",
            "10.0.0.1",
            capabilities=["lidar"],
        )

    def test_installs_missing_drivers(self):
        installed = []

        def installer(rid, driver):
            installed.append((rid, driver))
            return True

        resolver = DriverResolver(self.cap_registry, installer=installer)
        result = resolver.resolve("robot.sensor@A#1", ["driver.lidar"])
        self.assertTrue(result.satisfied)
        self.assertEqual(result.installed, ["driver.lidar"])
        self.assertEqual(result.missing, [])
        self.assertTrue(self.cap_registry.has_driver("robot.sensor@A#1", "driver.lidar"))

    def test_requests_when_installation_fails(self):
        requests = []

        def installer(_rid, _driver):
            return False

        def requester(rid, drivers):
            requests.append((rid, list(drivers)))

        resolver = DriverResolver(
            self.cap_registry,
            installer=installer,
            request_handler=requester,
        )
        result = resolver.resolve("robot.sensor@A#1", ["driver.lidar"])
        self.assertFalse(result.satisfied)
        self.assertEqual(result.installed, [])
        self.assertEqual(result.missing, ["driver.lidar"])
        self.assertEqual(requests, [("robot.sensor@A#1", ["driver.lidar"])])


class TestMeshDispatcher(unittest.TestCase):
    def setUp(self):
        registry = NodeRegistry(FakeRedis())
        manager = NodeManager(registry)
        self.cap_registry = CapabilityRegistry(manager)
        self.network = FakeNetwork()

    def test_prefers_ready_node(self):
        self.cap_registry.register(
            "robot.sensor@A#1",
            "10.0.0.1",
            capabilities=["lidar"],
            drivers=["driver.lidar"],
        )
        self.cap_registry.register(
            "robot.sensor@A#2",
            "10.0.0.2",
            capabilities=["lidar"],
        )

        dispatcher = MeshDispatcher(self.cap_registry, self.network)
        pack = {"name": "scan"}
        outcome = dispatcher.dispatch(
            pack,
            requirements={"capabilities": ["lidar"], "drivers": ["driver.lidar"]},
        )
        self.assertTrue(outcome.dispatched)
        self.assertEqual(outcome.target, "robot.sensor@A#1")
        self.assertEqual(self.network.sent[0][0], "10.0.0.1")
        self.assertEqual(outcome.attempted_targets, ["robot.sensor@A#1"])
        self.assertEqual(outcome.errors, [])

    def test_installs_driver_when_missing(self):
        self.cap_registry.register(
            "robot.sensor@A#2",
            "10.0.0.2",
            capabilities=["lidar"],
        )

        installed = []

        def installer(rid, driver):
            installed.append((rid, driver))
            return True

        resolver = DriverResolver(self.cap_registry, installer=installer)
        dispatcher = MeshDispatcher(self.cap_registry, self.network, driver_resolver=resolver)
        pack = {"name": "scan"}
        outcome = dispatcher.dispatch(
            pack,
            requirements={"capabilities": ["lidar"], "drivers": ["driver.lidar"]},
        )
        self.assertTrue(outcome.dispatched)
        self.assertEqual(installed, [("robot.sensor@A#2", "driver.lidar")])
        self.assertEqual(self.network.sent[0][0], "10.0.0.2")
        self.assertEqual(outcome.attempted_targets, ["robot.sensor@A#2"])
        self.assertEqual(outcome.errors, [])

    def test_falls_back_to_next_candidate_on_failed_install(self):
        self.cap_registry.register(
            "robot.sensor@A#1",
            "10.0.0.1",
            capabilities=["lidar"],
        )
        self.cap_registry.register(
            "robot.sensor@A#2",
            "10.0.0.2",
            capabilities=["lidar"],
        )

        def installer(rid, driver):
            return rid == "robot.sensor@A#2"

        resolver = DriverResolver(self.cap_registry, installer=installer)
        dispatcher = MeshDispatcher(self.cap_registry, self.network, driver_resolver=resolver)
        outcome = dispatcher.dispatch(
            {"name": "scan"},
            requirements={"capabilities": ["lidar"], "drivers": ["driver.lidar"]},
        )
        self.assertTrue(outcome.dispatched)
        self.assertEqual(outcome.target, "robot.sensor@A#2")
        self.assertEqual(outcome.attempted_targets, ["robot.sensor@A#1", "robot.sensor@A#2"])
        self.assertEqual(self.network.sent[0][0], "10.0.0.2")

    def test_reports_missing_when_install_fails(self):
        self.cap_registry.register(
            "robot.sensor@A#2",
            "10.0.0.2",
            capabilities=["lidar"],
        )

        def installer(_rid, _driver):
            return False

        requests = []

        def requester(rid, drivers):
            requests.append((rid, list(drivers)))

        resolver = DriverResolver(
            self.cap_registry,
            installer=installer,
            request_handler=requester,
        )
        dispatcher = MeshDispatcher(self.cap_registry, self.network, driver_resolver=resolver)
        pack = {"name": "scan"}
        outcome = dispatcher.dispatch(
            pack,
            requirements={"capabilities": ["lidar"], "drivers": ["driver.lidar"]},
        )
        self.assertEqual(outcome.status, "drivers_missing")
        self.assertEqual(outcome.missing_drivers, ["driver.lidar"])
        self.assertEqual(requests, [("robot.sensor@A#2", ["driver.lidar"])])
        self.assertEqual(self.network.sent, [])
        self.assertEqual(outcome.attempted_targets, ["robot.sensor@A#2"])
        self.assertEqual(outcome.errors, [])

    def test_reroutes_after_network_failure(self):
        class FlakyNetwork(FakeNetwork):
            def __init__(self):
                super().__init__()
                self.failures = {"10.0.0.1": 1}

            def send(self, recipient_id: str, message: dict):
                if self.failures.get(recipient_id, 0) > 0:
                    self.failures[recipient_id] -= 1
                    raise RuntimeError("link down")
                super().send(recipient_id, message)

        network = FlakyNetwork()
        monitor = DispatchMonitor()
        dispatcher = MeshDispatcher(
            self.cap_registry,
            network,
            monitor=monitor,
            retry_attempts=1,
            retry_backoff=0,
        )

        self.cap_registry.register(
            "robot.sensor@A#1",
            "10.0.0.1",
            capabilities=["lidar"],
            drivers=["driver.lidar"],
        )
        self.cap_registry.register(
            "robot.sensor@A#2",
            "10.0.0.2",
            capabilities=["lidar"],
            drivers=["driver.lidar"],
        )

        pack = {"name": "scan"}
        outcome = dispatcher.dispatch(
            pack,
            requirements={"capabilities": ["lidar"], "drivers": ["driver.lidar"]},
        )

        self.assertTrue(outcome.dispatched)
        self.assertEqual(outcome.target, "robot.sensor@A#2")
        self.assertIn("robot.sensor@A#1", ",".join(outcome.errors))
        events = monitor.recent()
        self.assertGreaterEqual(len(events), 2)
        self.assertEqual(events[-1].status, "dispatched")
        self.assertEqual(events[-1].target, "robot.sensor@A#2")
        failure_events = [event for event in events if event.status == "delivery_failed"]
        self.assertTrue(failure_events)
        self.assertIn("link down", failure_events[0].error)

    def test_monitor_records_latency(self):
        monitor = DispatchMonitor()
        dispatcher = MeshDispatcher(
            self.cap_registry,
            self.network,
            monitor=monitor,
        )

        self.cap_registry.register(
            "robot.sensor@A#1",
            "10.0.0.1",
            capabilities=["lidar"],
            drivers=["driver.lidar"],
        )

        pack = {"name": "scan", "id": "pack-123"}
        outcome = dispatcher.dispatch(
            pack,
            requirements={"capabilities": ["lidar"], "drivers": ["driver.lidar"]},
        )

        self.assertTrue(outcome.dispatched)
        events = monitor.recent()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertIsInstance(event, DispatchEvent)
        self.assertEqual(event.pack_id, "pack-123")
        self.assertEqual(event.status, "dispatched")
        self.assertGreaterEqual(event.latency_ms or 0.0, 0.0)

    def test_uses_pack_requirements_when_not_specified(self):
        dispatcher = MeshDispatcher(self.cap_registry, self.network)

        self.cap_registry.register(
            "robot.sensor@A#1",
            "10.0.0.1",
            capabilities=["lidar"],
            drivers=["driver.lidar"],
        )

        pack = {
            "name": "scan",
            "requirements": {"capabilities": ["lidar"], "drivers": ["driver.lidar"]},
        }

        outcome = dispatcher.dispatch(pack)

        self.assertTrue(outcome.dispatched)
        self.assertEqual(outcome.target, "robot.sensor@A#1")
        self.assertEqual(outcome.attempted_targets, ["robot.sensor@A#1"])


if __name__ == "__main__":
    unittest.main()
