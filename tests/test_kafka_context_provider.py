import unittest
from datetime import datetime, timedelta

from objects.context_query import ContextQuery

# patch KafkaConsumer before importing provider
from providers import kafka_context_provider

class DummyConsumer:
    def __init__(self, *args, **kwargs):
        self.messages = []

    def __iter__(self):
        return iter(self.messages)

    def close(self):
        pass

class DummyRecord:
    def __init__(self, value, timestamp=None):
        self.value = value
        self.timestamp = timestamp


class TestKafkaContextProvider(unittest.TestCase):
    def test_ingest_record(self):
        kafka_context_provider.KafkaConsumer = DummyConsumer
        provider = kafka_context_provider.KafkaContextProvider(
            "topic", bootstrap_servers="localhost", auto_start=False
        )
        now_ms = int(datetime.utcnow().timestamp() * 1000)
        record = DummyRecord(b'{"payload": {"foo": "bar"}}', now_ms)
        provider.ingest_record(record)
        query = ContextQuery(
            roles=[],
            time_range=(datetime.utcnow() - timedelta(seconds=1), datetime.utcnow() + timedelta(seconds=1)),
            scope="",
            data_type="",
        )
        results = provider.get_context(query)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["context"], {"foo": "bar"})


if __name__ == "__main__":
    unittest.main()
