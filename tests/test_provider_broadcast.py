import unittest
from datetime import datetime

from providers.memory_context_provider import MemoryContextProvider
from objects.context_data import ContextData
from objects.context_query import ContextQuery


class TestProviderBroadcast(unittest.TestCase):
    def test_broadcast_across_providers(self):
        p1 = MemoryContextProvider()
        p2 = MemoryContextProvider()
        p1.add_peer(p2)

        received = []
        p2.subscribe_context(lambda d: received.append(d))

        now = datetime.utcnow()
        p1.ingest_context({"msg": "hi"}, timestamp=now)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].payload, {"msg": "hi"})


if __name__ == "__main__":
    unittest.main()
