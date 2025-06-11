import unittest
from unittest.mock import MagicMock

from core.context_manager import ContextManager
from core.distributed_context_manager import DistributedContextManager
from interfaces.network_interface import NetworkInterface


class TestNetworkHooks(unittest.TestCase):
    def setUp(self):
        self.cache = ContextManager()
        self.network = MagicMock(spec=NetworkInterface)
        self.manager = DistributedContextManager(self.cache, self.network)

    def test_hook_triggered_on_update(self):
        captured = []
        self.manager.register_hook(lambda k, v: k == "task", lambda k, v, n: captured.append((k, v)))
        self.manager.update_context("task", {"a": 1})
        self.assertEqual(captured, [("task", {"a": 1})])

    def test_hook_can_use_network(self):
        self.manager.register_hook(lambda k, v: True, lambda k, v, n: n.broadcast({"event": k}))
        self.manager.update_context("t", {"b": 2})
        self.network.broadcast.assert_called_once_with({"event": "t"})


if __name__ == "__main__":
    unittest.main()
