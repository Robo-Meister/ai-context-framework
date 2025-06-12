import unittest
from datetime import datetime

from caiengine.parser.log_parser import LogParser


class TestLogParser(unittest.TestCase):
    def setUp(self):
        self.parser = LogParser()

    def test_parse_timestamp(self):
        log = "2025-05-21T10:00:00 ERROR Something bad"
        ts = self.parser.parse_timestamp(log)
        self.assertIsInstance(ts, datetime)
        self.assertEqual(ts.year, 2025)

    def test_detect_roles(self):
        log = "User connected"
        roles = self.parser.detect_roles(log)
        self.assertIn("user", roles)

        log2 = "Service restarted by root"
        roles2 = self.parser.detect_roles(log2)
        self.assertIn("admin", roles2)
        self.assertIn("service", roles2)

        log3 = "No role keywords"
        roles3 = self.parser.detect_roles(log3)
        self.assertEqual(roles3, ["unknown"])

    def test_detect_situations(self):
        log = "2025-05-21T10:00:00 ERROR timeout while accessing DB"
        situations = self.parser.detect_situations(log)
        self.assertIn("ERROR", situations)
        self.assertIn("network", situations)
        self.assertIn("database", situations)

        log2 = "DEBUG latency issue"
        situations2 = self.parser.detect_situations(log2)
        self.assertIn("DEBUG", situations2)

    def test_transform(self):
        log = "2025-05-21T09:15:23 ERROR Admin failed login attempt on server1"
        ctx = self.parser.transform(log)
        self.assertIsInstance(ctx["timestamp"], datetime)
        self.assertIn("admin", ctx["roles"])
        self.assertIn("security", ctx["situations"])
        self.assertIn("ERROR", ctx["situations"])
        self.assertEqual(ctx["content"], log)
    def test_transform_batch_multiline(self):
        multiline_logs = [
            "2025-05-21T10:00:00 ERROR Admin login failed",
            "Traceback (most recent call last):",
            "  File \"main.py\", line 10, in <module>",
            "    login_user()",
            "2025-05-21T10:01:00 INFO Service started"
        ]
        results = self.parser.transform_batch(multiline_logs)

        self.assertEqual(len(results), 2)
        self.assertIn("admin", results[0]["roles"])
        self.assertIn("security", results[0]["situations"])
        self.assertTrue("Traceback" in results[0]["content"])

        self.assertIn("service", results[1]["roles"])
        self.assertIn("INFO", results[1]["situations"])
if __name__ == "__main__":
    unittest.main()
