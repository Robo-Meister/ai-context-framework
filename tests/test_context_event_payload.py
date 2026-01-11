from datetime import datetime

from caiengine.providers.memory_context_provider import MemoryContextProvider


def test_context_event_payload_shape():
    provider = MemoryContextProvider()
    received = []
    provider.subscribe_context(received.append)

    provider.ingest_context(
        {"hello": "world"},
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        metadata={"id": "ctx-123", "roles": ["agent"], "content": "hello"},
        source_id="unit-test",
    )

    assert len(received) == 1
    event = received[0]

    assert event["context_id"] == "ctx-123"
    assert event["action"] == "context_update"
    assert event["status"] == "published"
    assert set(event["timestamps"].keys()) >= {"context_time", "event_time"}
    assert event["goal_metrics"] == {}

    context = event["context"]
    assert context["payload"] == {"hello": "world"}
    assert context["source_id"] == "unit-test"
    assert context["metadata"]["id"] == "ctx-123"
    assert context["roles"] == ["agent"]
    assert context["content"] == "hello"
