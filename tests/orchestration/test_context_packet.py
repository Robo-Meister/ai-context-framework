from caiengine.core.trust_module import TrustModule
from caiengine.interfaces.context_provider import ContextProvider
from caiengine.orchestration.context_packet import ContextPacketCompiler


def test_required_layers_always_included_if_present() -> None:
    compiler = ContextPacketCompiler()
    context = {
        "environment": {"camera": {"fps": 30}, "temperature": 22},
        "role": "operator",
        "network": {"quality": "good"},
    }

    packet = compiler.compile(
        context=context,
        required=["environment.camera", "role"],
        optional=["network"],
        budget={"max_layers": 2, "max_chars": 10},
    )

    assert "environment.camera" in packet.selected_layers
    assert "role" in packet.selected_layers
    assert "network" in packet.omitted_layers


def test_optional_layers_dropped_when_budget_exceeded_with_weight_order() -> None:
    compiler = ContextPacketCompiler()
    context = {
        "layer_a": {"payload": "A" * 40},
        "layer_b": {"payload": "B" * 40},
        "layer_c": {"payload": "C" * 40},
    }
    trust_module = TrustModule(weights={"layer_b": 0.9, "layer_a": 0.6, "layer_c": 0.2})

    packet = compiler.compile(
        context=context,
        required=[],
        optional=["layer_a", "layer_b", "layer_c"],
        budget={"max_layers": 1, "max_chars": 1_000, "trust_module": trust_module},
    )

    assert list(packet.selected_layers.keys()) == ["layer_b"]
    assert packet.omitted_layers == ["layer_a", "layer_c"]


def test_dot_notation_and_context_provider_weights_work() -> None:
    compiler = ContextPacketCompiler()
    provider = ContextProvider(
        context_weights={
            "environment": {"camera": 0.7, "temperature": 0.1},
            "network": 0.5,
        }
    )
    context = {
        "environment": {
            "camera": {"objects": ["person", "forklift"]},
            "temperature": 24,
        },
        "network": {"latency_ms": 12},
    }

    packet = compiler.compile(
        context=context,
        required=["environment.camera"],
        optional=["environment.temperature", "network"],
        budget={"max_layers": 2, "max_chars": 1_000, "context_provider": provider},
    )

    assert packet.selected_layers["environment.camera"]["objects"][0] == "person"
    # provider weights prefer network (0.5) over environment.temperature (0.1)
    assert "network" in packet.selected_layers
    assert "environment.temperature" in packet.omitted_layers


def test_nested_explicit_budget_weights_are_flattened() -> None:
    compiler = ContextPacketCompiler()
    context = {
        "environment": {"camera": {"fps": 30}},
        "network": {"latency_ms": 12},
    }

    packet = compiler.compile(
        context=context,
        required=[],
        optional=["network", "environment.camera"],
        budget={
            "max_layers": 1,
            "max_chars": 1_000,
            "weights": {"environment": {"camera": 0.9}, "network": 0.2},
        },
    )

    assert list(packet.selected_layers) == ["environment.camera"]
    assert "network" in packet.omitted_layers
