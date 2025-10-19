import json
import os
import tempfile
import unittest
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

    def test_logs_decode_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = os.path.join(tmp, "context.json")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("not valid json")

            provider = FileContextProvider(file_path)
            now = datetime.utcnow()
            query = ContextQuery(
                roles=[],
                time_range=(now - timedelta(seconds=1), now + timedelta(seconds=1)),
                scope="",
                data_type="",
            )
            with self.assertLogs(provider.logger.name, level="ERROR") as cm:
                provider.get_context(query)

            self.assertTrue(
                any("Failed to decode context file" in entry for entry in cm.output),
                cm.output,
            )


if __name__ == "__main__":
    unittest.main()
