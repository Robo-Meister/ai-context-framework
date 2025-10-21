import unittest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from caiengine.providers.http_context_provider import HTTPContextProvider
from caiengine.objects.context_query import ContextQuery
from caiengine.providers.memory_context_provider import MemoryContextProvider


class TestHTTPContextProvider(unittest.TestCase):
    def test_prepare_backend_from_path(self):
        provider = HTTPContextProvider(
            backend="caiengine.providers.simple_context_provider.SimpleContextProvider"
        )
        self.assertTrue(hasattr(provider.backend, "ingest_context"))
        self.assertTrue(hasattr(provider.backend, "get_context"))

    def test_prepare_backend_from_config(self):
        backend_config = {
            "path": "caiengine.providers.memory_context_provider.MemoryContextProvider",
            "options": {},
        }
        provider = HTTPContextProvider(backend=backend_config)
        self.assertIsInstance(provider.backend, MemoryContextProvider)

    def test_post_and_get(self):
        provider = HTTPContextProvider()
        client = TestClient(provider.app)

        now = datetime.utcnow()
        response = client.post(
            "/context",
            json={
                "payload": {"foo": "bar"},
                "timestamp": now.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("id", payload)

        response = client.get(
            "/context",
            params={
                "start": (now - timedelta(seconds=1)).isoformat(),
                "end": (now + timedelta(seconds=1)).isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertIn("items", results)
        self.assertEqual(len(results["items"]), 1)

        query = ContextQuery(
            roles=[],
            time_range=(now - timedelta(seconds=1), now + timedelta(seconds=1)),
            scope="",
            data_type="",
        )
        backend_results = provider.get_context(query)
        self.assertEqual(len(backend_results), 1)


if __name__ == "__main__":
    unittest.main()
