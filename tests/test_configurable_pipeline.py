import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from caiengine.pipelines.configurable_pipeline import ConfigurablePipeline
from caiengine.pipelines.configurable_pipeline import _PROVIDER_MAP
from caiengine.providers.sqlite_context_provider import SQLiteContextProvider
from caiengine.common import AuditLogger


class TestConfigurablePipeline(unittest.TestCase):
    def test_build_and_run_goal(self):
        cfg = {
            "provider": {"type": "memory"},
            "candidates": [
                {"category": "foo", "context": {"foo": "bar"}, "base_weight": 1.0}
            ],
            "policy": "simple",
            "trust_weights": {"foo": 1.0},
            "feedback": {"type": "goal", "goal_state": {"progress": 10}},
        }
        pipeline = ConfigurablePipeline.from_dict(cfg)
        now = datetime.utcnow()
        data_batch = [
            {
                "timestamp": now,
                "context": {"foo": "bar"},
                "roles": [],
                "situations": [],
                "role": "user",
                "content": "text",
                "confidence": 1.0,
            }
        ]
        result = pipeline.run(data_batch)
        self.assertEqual(len(result), 1)
        self.assertIn("goal_suggestion", result[0])

    def test_registered_provider_keys(self):
        expected_keys = {
            "memory",
            "simple",
            "mock",
            "json",
            "file",
            "xml",
            "csv",
            "ocr",
            "http",
            "redis",
            "kafka",
            "sqlite",
            "mysql",
            "postgres",
            "postgresql",
        }
        self.assertTrue(expected_keys.issubset(_PROVIDER_MAP.keys()))

    def test_pipeline_with_sqlite_provider(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "context.db"
            cfg = {
                "provider": {"type": "sqlite", "args": {"db_path": str(db_path)}},
                "candidates": [
                    {
                        "category": "support",
                        "context": {"channel": "email"},
                        "base_weight": 1.0,
                    }
                ],
            }
            pipeline = ConfigurablePipeline.from_dict(cfg)
            self.assertIsInstance(pipeline.provider, SQLiteContextProvider)

            now = datetime.utcnow()
            data_batch = [
                {
                    "timestamp": now,
                    "context": {"channel": "email"},
                    "roles": [],
                    "situations": [],
                    "role": "user",
                    "content": "Ticket update",
                    "confidence": 1.0,
                }
            ]

            results = pipeline.run(data_batch)
            self.assertIsInstance(results, list)

    def test_pipeline_logs_token_usage_events(self):
        audit_logger = AuditLogger()
        cfg = {
            "provider": {"type": "memory"},
            "candidates": [
                {
                    "category": "support",
                    "context": {"channel": "email"},
                    "base_weight": 1.0,
                }
            ],
            "feedback": {"type": "goal"},
        }

        pipeline = ConfigurablePipeline.from_dict(cfg, audit_logger=audit_logger)

        now = datetime.utcnow()
        data_batch = [
            {
                "timestamp": now,
                "context": {"channel": "email"},
                "roles": [],
                "situations": [],
                "role": "user",
                "content": "Ticket update",
                "confidence": 1.0,
            }
        ]

        results = pipeline.run(data_batch)

        records = audit_logger.get_records()
        usage_records = [
            record for record in records if record["step"] == "token_usage"
        ]
        self.assertTrue(usage_records, "token usage events should be audited")
        detail = usage_records[0]["detail"]
        self.assertEqual(detail["provider"], "memory")
        inferred_category = results[0]["category"] if results else None
        self.assertEqual(detail["category"], inferred_category)
        self.assertIn("usage", detail)
        self.assertGreater(detail["usage"]["total_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
