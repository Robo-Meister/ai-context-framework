import unittest
from unittest.mock import MagicMock
from caiengine.core.context_manager import ContextManager
from caiengine.interfaces.network_interface import NetworkInterface
from caiengine.core.distributed_context_manager import DistributedContextManager


class TestDistributedContextManager(unittest.TestCase):
    def setUp(self):
        self.cache = ContextManager()
        self.network = MagicMock(spec=NetworkInterface)
        self.ctx_mgr = DistributedContextManager(self.cache, self.network)

    def test_update_context_stores_in_cache_and_broadcasts(self):
        key = "task_123"
        value = {"status": "in_progress"}

        self.ctx_mgr.update_context(key, value)

        # Assert cache updated
        self.assertEqual(self.cache.get(key), value)

        # Assert network send called
        self.network.send.assert_called_once_with("all_nodes", {"key": key, "value": value})

    def test_receive_updates_applies_remote_change(self):
        key = "task_456"
        value = {"status": "done"}

        # Simulate network receiving a message
        self.network.receive.return_value = {"message": {"key": key, "value": value}}

        self.ctx_mgr.receive_updates()

        # Assert the cache was updated with remote data
        self.assertEqual(self.cache.get(key), value)

    def test_receive_updates_ignores_empty(self):
        self.network.receive.return_value = None
        self.ctx_mgr.receive_updates()
        # No exception = pass

