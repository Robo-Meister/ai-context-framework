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
tasks_mod = _load("caiengine.network.node_tasks", "node_tasks.py")
agent_mod = _load("caiengine.network.node_agent", "node_agent.py")

RoboId = roboid.RoboId
NodeRegistry = registry_mod.NodeRegistry
HeartbeatStore = heartbeats_mod.HeartbeatStore
RedisNodeTaskQueue = tasks_mod.RedisNodeTaskQueue
NodeAgent = agent_mod.NodeAgent


class NodeAgentTest(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.registry = NodeRegistry(self.redis)
        self.heartbeats = HeartbeatStore(self.redis)
        self.queue = RedisNodeTaskQueue(self.redis)

    def test_agent_registers_and_beats(self):
        agent = NodeAgent(
            "robot.control@test#1",
            self.registry,
            self.heartbeats,
            self.queue,
            heartbeat_interval=0.02,
        )

        agent.start(
            "10.0.0.1",
            capabilities=["camera"],
            metadata={"zone": "lab"},
        )

        time.sleep(0.05)
        record = self.registry.get("robot.control@test#1")
        self.assertEqual(record["address"], "10.0.0.1")
        self.assertIn("camera", record["capabilities"])
        last_seen = self.heartbeats.last_seen("robot.control@test#1")
        self.assertIsNotNone(last_seen)
        self.assertLess(time.time() - last_seen, 1)

        agent.stop(deregister=True)
        self.assertIsNone(self.registry.get("robot.control@test#1"))

    def test_agent_processes_tasks(self):
        handled = []

        def handler(task):
            handled.append(task.payload)

        agent = NodeAgent(
            "robot.worker@test#1",
            self.registry,
            self.heartbeats,
            self.queue,
            heartbeat_interval=0.02,
            task_poll_interval=0.01,
        )

        agent.start("10.0.0.5", task_handler=handler)
        self.queue.enqueue("robot.worker@test#1", {"op": "calibrate"})
        time.sleep(0.05)

        self.assertTrue(handled)
        self.assertEqual(handled[0]["op"], "calibrate")
        agent.stop()

    def test_snapshot_includes_latest_state(self):
        agent = NodeAgent(
            "robot.worker@test#9",
            self.registry,
            self.heartbeats,
            self.queue,
            heartbeat_interval=0.02,
        )

        agent.start("10.0.0.9", capabilities=["lift"], drivers=["arm"], apps=["haul"])
        time.sleep(0.03)
        snapshot = agent.snapshot()
        self.assertEqual(snapshot["robo_id"], "robot.worker@test#9")
        self.assertEqual(snapshot["address"], "10.0.0.9")
        self.assertIn("lift", snapshot["capabilities"])
        self.assertIn("arm", snapshot["drivers"])
        self.assertIn("haul", snapshot["apps"])
        self.assertIsNotNone(snapshot["heartbeat"])
        agent.stop()


if __name__ == "__main__":
    unittest.main()

