import unittest
from datetime import datetime, timedelta

from caiengine.providers.context_engine_provider import ContextEngineProvider
from caiengine.objects.context_query import ContextQuery


class FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value):
        self.store[key] = value

    def get(self, key):
        return self.store.get(key)

    def keys(self, pattern):
        import fnmatch
        return [k for k in self.store if fnmatch.fnmatch(k, pattern)]


class TestContextEngineProvider(unittest.TestCase):
    def test_recursive_fetch(self):
        r = FakeRedis()
        provider = ContextEngineProvider(r)
        provider.register_link("User", "client_id", "Client")
        now = datetime.utcnow()
        provider.ingest_context("User", "paul", "client_id", "5001", timestamp=now)
        provider.ingest_context("User", "paul", "level", "A2", timestamp=now)
        provider.ingest_context("Client", "5001", "topic", "Chinese", timestamp=now)

        query = ContextQuery(
            roles=[],
            time_range=(now - timedelta(seconds=1), now + timedelta(seconds=1)),
            scope="User:paul",
            data_type="",
        )
        result = provider.get_context(query)
        self.assertEqual(result[0]["context"]["topic"], "Chinese")
        self.assertEqual(result[0]["context"]["level"], "A2")
        self.assertEqual(result[0]["context"]["client_id"], "5001")


if __name__ == "__main__":
    unittest.main()
