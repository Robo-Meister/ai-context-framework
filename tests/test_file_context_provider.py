import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta

from caiengine.providers.file_context_provider import FileContextProvider
from caiengine.objects.context_query import ContextQuery


class TestFileContextProvider(unittest.TestCase):
    def test_persist_and_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = os.path.join(tmp, "context.json")
            provider = FileContextProvider(file_path)
            now = datetime.utcnow()
            provider.ingest_context({"value": 1}, timestamp=now)
            query = ContextQuery(roles=[], time_range=(now - timedelta(seconds=1), now + timedelta(seconds=1)), scope="", data_type="")
            results = provider.get_context(query)
            self.assertEqual(len(results), 1)
            # verify file contents
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
            # reload provider from disk
            provider2 = FileContextProvider(file_path)
            results2 = provider2.get_context(query)
            self.assertEqual(len(results2), 1)


if __name__ == "__main__":
    unittest.main()
