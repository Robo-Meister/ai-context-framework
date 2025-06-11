import unittest
from datetime import datetime, timedelta

from providers.simple_context_provider import SimpleContextProvider
import objects.context_query as ContextQuery


class TestSimpleContextProvider(unittest.TestCase):
    def test_basic_ingest_and_fetch(self):
        provider = SimpleContextProvider()
        now = datetime.utcnow()
        query = ContextQuery.ContextQuery(roles=[], time_range=(now - timedelta(seconds=1), now + timedelta(seconds=1)), scope="", data_type="")
        provider.ingest_context({"foo": "bar"}, timestamp=now)
        results = provider.get_context(query)
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
