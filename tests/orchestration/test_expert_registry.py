from caiengine.orchestration import DummyExpert, ExpertRegistry
from caiengine.orchestration.expert_types import ExpertResult


class SampleExpert:
    def run(self, input: dict, context: dict) -> ExpertResult:
        return ExpertResult(output={"input": input, "context": context}, confidence=1.0)


def test_register_and_get_expert() -> None:
    registry = ExpertRegistry()
    expert = SampleExpert()

    expert_id = registry.register(expert, capabilities={"task": "classify"})

    assert expert_id == "SampleExpert"
    assert registry.get(expert_id) is expert


def test_list_experts_returns_entries() -> None:
    registry = ExpertRegistry()
    first = SampleExpert()
    second = DummyExpert()

    registry.register(first, capabilities={"task": "classify", "tags": ["nlp"]})
    registry.register(second, capabilities={"task": "fallback", "layers": ["dummy"]})

    entries = registry.list_experts()

    assert len(entries) == 2
    assert {entry.expert_id for entry in entries} == {"SampleExpert", "dummy_expert"}


def test_match_filters_by_task_tags_and_layers() -> None:
    registry = ExpertRegistry()
    registry.register(
        SampleExpert(),
        capabilities={"task": "classify", "tags": ["nlp", "text"], "layers": ["l1"]},
    )
    registry.register(
        DummyExpert(),
        capabilities={"task": "fallback", "tags": ["debug"], "layers": ["dummy"]},
    )

    matches = registry.match({"task": "classify", "tags": ["nlp"], "layers": ["l1"]})

    assert len(matches) == 1
    assert matches[0].expert_id == "SampleExpert"


def test_match_handles_null_tags_and_layers_criteria() -> None:
    registry = ExpertRegistry()
    registry.register(
        SampleExpert(),
        capabilities={"task": "classify", "tags": ["nlp"], "layers": ["l1"]},
    )

    matches = registry.match({"task": "classify", "tags": None, "layers": None})

    assert len(matches) == 1
    assert matches[0].expert_id == "SampleExpert"
