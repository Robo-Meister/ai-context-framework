import unittest
import importlib.util
from pathlib import Path
import sys

MODULE_PATH = Path(__file__).resolve().parents[2]

# Load RoboId so relative import in session_manager works
ROBOID_PATH = MODULE_PATH / "src" / "caiengine" / "network" / "roboid.py"
spec_roboid = importlib.util.spec_from_file_location("caiengine.network.roboid", ROBOID_PATH)
roboid_module = importlib.util.module_from_spec(spec_roboid)
spec_roboid.loader.exec_module(roboid_module)
sys.modules['caiengine.network.roboid'] = roboid_module

# Load SessionManager
SM_PATH = MODULE_PATH / "src" / "caiengine" / "network" / "session_manager.py"
spec = importlib.util.spec_from_file_location("caiengine.network.session_manager", SM_PATH)
session_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session_module)
SessionManager = session_module.SessionManager
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


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.manager = SessionManager(self.redis)

    def test_start_and_sessions(self):
        rid = RoboId.parse("robot.control@A#1")
        self.manager.start("sess1", ["nodeA", rid])
        sessions = self.manager.sessions()
        self.assertEqual(sessions["sess1"], ["nodeA", str(rid)])

    def test_end(self):
        self.manager.start("sess2", ["nodeA", "nodeB"])
        self.manager.end("sess2")
        self.assertNotIn("sess2", self.manager.sessions())


if __name__ == "__main__":
    unittest.main()
