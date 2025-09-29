import time
import unittest

from pathlib import Path
import importlib.util
import sys

from .fakes import FakeRedis

MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "caiengine" / "network"


def _load(module_name: str, relative: str):
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


roboid = _load("caiengine.network.roboid", "roboid.py")
tasks_mod = _load("caiengine.network.node_tasks", "node_tasks.py")

RoboId = roboid.RoboId
RedisNodeTaskQueue = tasks_mod.RedisNodeTaskQueue


class NodeTaskQueueTest(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.queue = RedisNodeTaskQueue(self.redis)

    def test_enqueue_and_dequeue(self):
        rid = RoboId.parse("robot.control@test#1")
        enqueued = self.queue.enqueue(rid, {"op": "ping"})
        self.assertEqual(enqueued.payload["op"], "ping")
        self.assertIsNotNone(enqueued.task_id)

        dequeued = self.queue.dequeue(rid)
        self.assertIsNotNone(dequeued)
        self.assertEqual(dequeued.task_id, enqueued.task_id)
        self.assertGreaterEqual(dequeued.created_at, enqueued.created_at)

    def test_blocking_pop_waits_until_available(self):
        rid = "robot.worker@test#2"

        def delayed_enqueue():
            time.sleep(0.05)
            self.queue.enqueue(rid, {"op": "start"})

        import threading

        t = threading.Thread(target=delayed_enqueue)
        t.start()
        task = self.queue.dequeue(rid, block=True, timeout=0.2)
        t.join()

        self.assertIsNotNone(task)
        self.assertEqual(task.payload["op"], "start")


if __name__ == "__main__":
    unittest.main()

