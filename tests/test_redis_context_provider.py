import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from src.caiengine.objects.context_query import ContextQuery
from src.caiengine.providers import redis_context_provider


class DummyThread:
    def __init__(self, target=None, daemon=None):
        self.target = target
        self.daemon = daemon

    def start(self):
        # Prevent the background listener thread from running during tests.
        return None


class FakePubSub:
    def __init__(self):
        self.channels = []

    def subscribe(self, channel):
        self.channels.append(channel)

    def listen(self):  # pragma: no cover - the listener thread is disabled in tests
        if False:
            yield


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.expiries = {}
        self.published = []
        self._pubsub = FakePubSub()

    def set(self, key, value):
        self.store[key] = value

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.expiries[key] = ttl

    def get(self, key):
        return self.store.get(key)

    def keys(self, pattern):
        if not pattern.endswith("*"):
            return [key for key in self.store if key == pattern]
        prefix = pattern[:-1]
        return [key for key in self.store if key.startswith(prefix)]

    def publish(self, channel, data):
        self.published.append((channel, data))

    def pubsub(self):
        return self._pubsub


@pytest.fixture
def fake_redis_provider(monkeypatch):
    fake = FakeRedis()
    fake_module = SimpleNamespace(
        Redis=SimpleNamespace(from_url=lambda url, decode_responses=True: fake)
    )
    monkeypatch.setattr(redis_context_provider, "redis", fake_module)
    monkeypatch.setattr(redis_context_provider.threading, "Thread", DummyThread)
    provider = redis_context_provider.RedisContextProvider("redis://localhost", key_prefix="ctx:")
    return provider, fake


def test_ingest_context_persists_payload(fake_redis_provider):
    provider, fake = fake_redis_provider
    now = datetime.utcnow()

    context_id = provider.ingest_context(
        {"foo": "bar"}, timestamp=now, metadata={"roles": ["test"]}, ttl=60
    )

    base = f"{provider.key_prefix}{context_id}"
    assert fake.store[f"{base}:payload"] == json.dumps({"foo": "bar"})
    assert fake.store[f"{base}:timestamp"] == now.isoformat()
    assert json.loads(fake.store[f"{base}:metadata"]) == {
        "roles": ["test"],
        "id": context_id,
    }
    # Confidence defaults to 1.0 and should be string encoded for storage.
    assert fake.store[f"{base}:confidence"] == "1.0"
    # TTL should be applied to each stored key.
    assert set(fake.expiries) == {
        f"{base}:payload",
        f"{base}:timestamp",
        f"{base}:metadata",
        f"{base}:source_id",
        f"{base}:confidence",
    }


def test_fetch_context_applies_time_filter(fake_redis_provider):
    provider, _ = fake_redis_provider
    early = datetime.utcnow() - timedelta(days=2)
    recent = datetime.utcnow()

    provider.ingest_context({"old": True}, timestamp=early)
    recent_id = provider.ingest_context({"old": False}, timestamp=recent)

    window = ContextQuery(time_range=(datetime.utcnow() - timedelta(hours=1), datetime.utcnow()))
    results = provider.fetch_context(window)

    assert len(results) == 1
    assert results[0].payload == {"old": False}
    assert results[0].metadata.get("id") == recent_id


def test_ingest_context_notifies_subscribers(fake_redis_provider):
    provider, fake = fake_redis_provider
    received = []

    provider.subscribe_context(lambda ctx: received.append(ctx))
    context_id = provider.ingest_context({"hello": "world"})

    assert len(received) == 1
    assert received[0].payload == {"hello": "world"}
    assert fake.published == [("context:new", context_id)]
