from datetime import datetime, timedelta

from caiengine.objects.context_query import ContextQuery
from caiengine.orchestration import ExpertRegistry, ExpertResult
from caiengine.pipelines.orchestrated_pipeline import OrchestratedPipeline
from caiengine.providers.memory_context_provider import MemoryContextProvider


class DummyExpert:
    def __init__(self, expert_id: str, confidence: float) -> None:
        self.expert_id = expert_id
        self._confidence = confidence

    def run(self, input: dict, context: dict) -> ExpertResult:
        return ExpertResult(
            output={"expert": self.expert_id, "context_packet": context.get("context_packet", {})},
            confidence=self._confidence,
            debug={"expert": self.expert_id},
            used_layers=["retrieved.items"],
            model_id=self.expert_id,
            model_version="1",
        )


def test_orchestrated_pipeline_end_to_end_includes_telemetry() -> None:
    provider = MemoryContextProvider()
    now = datetime.utcnow()
    provider.ingest_context(
        payload={"topic": "deployment", "status": "green"},
        timestamp=now,
        metadata={"roles": ["assistant"], "content": "deploy context"},
    )
    provider.ingest_context(
        payload={"topic": "alerts", "status": "quiet"},
        timestamp=now + timedelta(seconds=1),
        metadata={"roles": ["assistant"], "content": "alert context"},
    )

    registry = ExpertRegistry()
    registry.register(
        DummyExpert("expert_low", 0.4),
        capabilities={"category": "analysis", "scope": "global", "tags": ["text"], "layers": ["retrieved.items"]},
    )
    registry.register(
        DummyExpert("expert_high", 0.9),
        capabilities={"category": "analysis", "scope": "global", "tags": ["text"], "layers": ["retrieved.items"]},
    )

    pipeline = OrchestratedPipeline(context_provider=provider, registry=registry)

    result = pipeline.run(
        request={"category": "analysis", "scope": "global", "tags": ["text"]},
        goal_context={"required_layers": ["retrieved.items"], "optional_layers": ["goal"]},
    )

    assert result["response"]["output"]["expert"] == "expert_high"
    assert result["response"]["selected_experts"] == ["expert_low", "expert_high"]

    telemetry = result["telemetry"]
    assert telemetry["selected_layers"] == ["retrieved.items", "goal"]
    assert telemetry["chosen_experts"] == ["expert_low", "expert_high"]
    assert telemetry["confidences"] == [0.4, 0.9]


def test_orchestrated_pipeline_is_deterministic_for_equal_confidence() -> None:
    provider = MemoryContextProvider()
    provider.ingest_context(payload={"topic": "ops"}, metadata={"roles": ["assistant"], "content": "ops context"})

    registry = ExpertRegistry()
    registry.register(
        DummyExpert("expert_first", 0.7),
        capabilities={"category": "analysis", "scope": "global", "tags": ["text"], "layers": ["retrieved.items"]},
    )
    registry.register(
        DummyExpert("expert_second", 0.7),
        capabilities={"category": "analysis", "scope": "global", "tags": ["text"], "layers": ["retrieved.items"]},
    )

    pipeline = OrchestratedPipeline(context_provider=provider, registry=registry)

    request = {"category": "analysis", "scope": "global", "tags": ["text"]}
    first = pipeline.run(request=request, goal_context={"required_layers": ["retrieved.items"]})
    second = pipeline.run(request=request, goal_context={"required_layers": ["retrieved.items"]})

    assert first["response"]["output"]["expert"] == "expert_first"
    assert second["response"]["output"]["expert"] == "expert_first"
    assert first["telemetry"] == second["telemetry"]


class QueryAwareProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.last_query = None

    def get_context(self, query: ContextQuery):
        self.calls += 1
        self.last_query = query
        return []


class ZeroArgProvider:
    def __init__(self) -> None:
        self.calls = 0

    def get_context(self):
        self.calls += 1
        return []


def test_get_context_supports_provider_with_query_argument() -> None:
    provider = QueryAwareProvider()
    pipeline = OrchestratedPipeline(context_provider=provider, registry=ExpertRegistry())

    query = ContextQuery(time_range=(datetime(2025, 1, 1), datetime(2025, 1, 2)))
    context = pipeline._get_context(query)

    assert context == []
    assert provider.calls == 1
    assert provider.last_query is query


def test_get_context_supports_provider_without_query_argument() -> None:
    provider = ZeroArgProvider()
    pipeline = OrchestratedPipeline(context_provider=provider, registry=ExpertRegistry())

    query = ContextQuery(time_range=(datetime(2025, 1, 1), datetime(2025, 1, 2)))
    context = pipeline._get_context(query)

    assert context == []
    assert provider.calls == 1


def test_build_query_accepts_list_time_range() -> None:
    pipeline = OrchestratedPipeline(context_provider=ZeroArgProvider(), registry=ExpertRegistry())

    start = datetime(2025, 1, 1)
    end = datetime(2025, 1, 2)
    query = pipeline._build_query(request={"time_range": [start, end]}, goal_context={})

    assert query.time_range == (start, end)
