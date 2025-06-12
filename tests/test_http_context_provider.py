import unittest
from datetime import datetime, timedelta
import json
from urllib import request, parse

from caiengine.providers.http_context_provider import HTTPContextProvider
from caiengine.objects.context_query import ContextQuery


class TestHTTPContextProvider(unittest.TestCase):
    def test_post_and_get(self):
        provider = HTTPContextProvider(host="127.0.0.1", port=8099)
        provider.start()
        try:
            now = datetime.utcnow()
            url = "http://127.0.0.1:8099/context"
            data = {
                "payload": {"foo": "bar"},
                "timestamp": now.isoformat(),
            }
            req = request.Request(url, data=json.dumps(data).encode(), method="POST", headers={"Content-Type": "application/json"})
            with request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                payload = json.loads(resp.read())
                self.assertIn("id", payload)

            query = ContextQuery(roles=[], time_range=(now - timedelta(seconds=1), now + timedelta(seconds=1)), scope="", data_type="")
            # fetch via HTTP GET
            q = parse.urlencode({
                "start": (now - timedelta(seconds=1)).isoformat(),
                "end": (now + timedelta(seconds=1)).isoformat(),
            })
            with request.urlopen(f"{url}?{q}") as resp:
                self.assertEqual(resp.status, 200)
                results = json.loads(resp.read())
                self.assertEqual(len(results), 1)
        finally:
            provider.stop()


if __name__ == "__main__":
    unittest.main()
