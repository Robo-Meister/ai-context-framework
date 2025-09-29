import importlib.util
from pathlib import Path
import sys
import time
from typing import Any, Dict, Optional

MODULE_PATH = Path(__file__).resolve().parents[2]


# Provide lightweight package stubs so relative imports inside the modules do
# not trigger heavy optional dependencies from the package ``__init__`` files.
if "caiengine" not in sys.modules:
    import types

    caiengine_pkg = types.ModuleType("caiengine")
    caiengine_pkg.__path__ = [str(MODULE_PATH / "src" / "caiengine")]
    sys.modules["caiengine"] = caiengine_pkg

    network_pkg = types.ModuleType("caiengine.network")
    network_pkg.__path__ = [str(MODULE_PATH / "src" / "caiengine" / "network")]
    sys.modules["caiengine.network"] = network_pkg

    interfaces_pkg = types.ModuleType("caiengine.interfaces")
    interfaces_pkg.__path__ = [str(MODULE_PATH / "src" / "caiengine" / "interfaces")]
    sys.modules["caiengine.interfaces"] = interfaces_pkg


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[name] = module
    return module


NetworkInterface = load_module(
    "caiengine.interfaces.network_interface",
    MODULE_PATH / "src" / "caiengine" / "interfaces" / "network_interface.py",
).NetworkInterface

NetworkManager = load_module(
    "caiengine.network.network_manager",
    MODULE_PATH / "src" / "caiengine" / "network" / "network_manager.py",
).NetworkManager

NodeRegistry = load_module(
    "caiengine.network.node_registry",
    MODULE_PATH / "src" / "caiengine" / "network" / "node_registry.py",
).NodeRegistry

SimpleNetworkMock = load_module(
    "caiengine.network.simple_network",
    MODULE_PATH / "src" / "caiengine" / "network" / "simple_network.py",
).SimpleNetworkMock


class FakeRedis:
    def __init__(self):
        self.store: Dict[str, Dict[str, Any]] = {}

    def hset(self, key: str, field: str, value: Any) -> None:
        self.store.setdefault(key, {})[field] = value

    def hdel(self, key: str, field: str) -> None:
        if key in self.store:
            self.store[key].pop(field, None)

    def hgetall(self, key: str) -> Dict[str, Any]:
        return self.store.get(key, {}).copy()

    def hget(self, key: str, field: str) -> Optional[Any]:
        return self.store.get(key, {}).get(field)


class RecordingNetwork(NetworkInterface):
    def __init__(self):
        self.sent = []

    def send(self, recipient_id: str, message: dict):
        self.sent.append((recipient_id, message))

    def broadcast(self, message: dict):  # pragma: no cover - not used in tests
        self.sent.append(("*", message))

    def receive(self):  # pragma: no cover - dispatcher drives sends only
        return None

    def start_listening(self, _on_network_message):  # pragma: no cover - noop
        return None


def test_network_manager_invokes_callback():
    net = SimpleNetworkMock()
    mgr = NetworkManager(net)
    received = []

    mgr.start_listening(lambda msg: received.append(msg))
    net.send("node1", {"ping": "pong"})
    time.sleep(0.1)
    mgr.stop_listening()

    assert {"ping": "pong"} in received


def test_simple_network_mock_start_listening():
    net = SimpleNetworkMock()
    received = []
    net.start_listening(lambda msg: received.append(msg))
    net.send("node1", {"foo": "bar"})
    time.sleep(0.1)
    net.stop_listening()

    assert {"foo": "bar"} in received


def test_network_manager_handles_mesh_registration_and_dispatch():
    redis = FakeRedis()
    registry = NodeRegistry(redis)
    network = RecordingNetwork()
    manager = NetworkManager(network, node_registry=registry)

    manager.register_node(
        "robot.control@A#1",
        "addr-1",
        capabilities=["weld", "lift"],
        drivers=["driver.welder"],
    )
    manager.register_node(
        "robot.control@A#2",
        "addr-2",
        capabilities=["lift"],
    )

    # Requirement should match only the first node because of the driver
    pack = {"id": "job-1", "requirements": {"drivers": ["driver.welder"]}}
    outcome = manager.dispatch_to_mesh(pack)

    assert outcome.dispatched
    assert outcome.target == "robot.control@A#1"
    assert network.sent[0][0] == "addr-1"
    # Ensure the manager exposes node lookup helpers
    matches = manager.find_nodes(capabilities=["lift"])
    assert set(matches.keys()) == {"robot.control@A#1", "robot.control@A#2"}

