import time
import unittest
import importlib.util
import sys
from pathlib import Path

from .fakes import FakeRedis

MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "caiengine" / "network"


def _load(module_name: str, relative: str):
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


roboid = _load("caiengine.network.roboid", "roboid.py")
registry_mod = _load("caiengine.network.node_registry", "node_registry.py")
heartbeats_mod = _load("caiengine.network.heartbeats", "heartbeats.py")
discovery_mod = _load("caiengine.network.discovery", "discovery.py")

NodeRegistry = registry_mod.NodeRegistry
HeartbeatStore = heartbeats_mod.HeartbeatStore
NodeDiscoveryService = discovery_mod.NodeDiscoveryService
WebSocketDiscoveryClient = discovery_mod.WebSocketDiscoveryClient


class DiscoveryServiceTest(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.registry = NodeRegistry(self.redis)
        self.heartbeats = HeartbeatStore(self.redis)

    def test_process_gossip_message_updates_registry(self):
        service = NodeDiscoveryService(self.registry, self.heartbeats)
        payload = {
            "robo_id": "robot.control@test#3",
            "address": "10.1.0.3",
            "capabilities": ["camera"],
            "meta": {"zone": "alpha"},
            "heartbeat": time.time(),
        }
        service.process_gossip_message(payload)

        record = self.registry.get("robot.control@test#3")
        self.assertEqual(record["address"], "10.1.0.3")
        self.assertIn("camera", record["capabilities"])
        self.assertEqual(self.heartbeats.last_seen("robot.control@test#3"), payload["heartbeat"])

    def test_prune_stale_nodes_removes_expired_entries(self):
        service = NodeDiscoveryService(self.registry, self.heartbeats, clock=lambda: 100.0)
        self.registry.join("robot.worker@test#4", "10.2.0.4")
        self.heartbeats.beat("robot.worker@test#4", timestamp=50.0)

        service.prune_stale_nodes(max_age=10.0)
        self.assertIsNone(self.registry.get("robot.worker@test#4"))

    def test_websocket_fallback_used_when_pubsub_missing(self):
        events = []

        def ws_factory():
            def generator():
                yield {
                    "robo_id": "robot.worker@test#5",
                    "address": "10.3.0.5",
                    "capabilities": ["lift"],
                }

            client = WebSocketDiscoveryClient(lambda: generator())
            events.append("started")
            return client

        redis = FakeRedis(pubsub_available=False)
        service = NodeDiscoveryService(
            NodeRegistry(redis),
            HeartbeatStore(redis),
            redis_client=redis,
            websocket_client_factory=ws_factory,
        )
        service.start()
        time.sleep(0.05)
        service.stop()

        self.assertIn("started", events)
        record = service.registry.get("robot.worker@test#5")
        self.assertEqual(record["address"], "10.3.0.5")


if __name__ == "__main__":
    unittest.main()

