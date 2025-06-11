import unittest
import time
from datetime import datetime, timedelta
from providers.memory_context_provider import MemoryContextProvider
import objects.context_query as ContextQuery


class TestMemoryContextProvider(unittest.TestCase):
    def test_ingest_and_fetch_with_ttl(self):
        provider = MemoryContextProvider()
        now = datetime.utcnow()
        query = ContextQuery.ContextQuery(roles=[], time_range=(now - timedelta(seconds=1), now + timedelta(seconds=2)), scope="", data_type="")
        provider.ingest_context({"x": 1}, timestamp=now, metadata={}, ttl=1)
        self.assertEqual(len(provider.get_context(query)), 1)
        time.sleep(1.1)
        self.assertEqual(len(provider.get_context(query)), 0)

if __name__ == "__main__":
    unittest.main()
