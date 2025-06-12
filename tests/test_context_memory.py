import unittest
import time
from caiengine.core.context_manager import ContextManager

class TestContextManagerMemory(unittest.TestCase):
    def test_cache_expiration(self):
        cm = ContextManager()
        cm.update_context("user1", {"a": 1}, ttl=1)
        self.assertEqual(cm.get("user1"), {"a": 1})
        time.sleep(1.1)
        self.assertEqual(cm.get("user1"), {})

    def test_history_tracking(self):
        cm = ContextManager()
        cm.update_context("task", {"s": "one"})
        cm.update_context("task", {"s": "two"})
        history = cm.get_history("task")
        self.assertEqual(len(history), 2)
        self.assertTrue(any(h["data"] == {"s": "one"} for h in history))
        self.assertTrue(any(h["data"] == {"s": "two"} for h in history))

if __name__ == "__main__":
    unittest.main()
