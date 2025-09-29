import os

os.environ.setdefault("CAIENGINE_LIGHT_IMPORT", "1")

from caiengine.cai_bridge import CAIBridge
from caiengine.commands import COMMAND


def test_cai_bridge_personality_changes_suggestions():
    history = [{"progress": 0}]
    actions = [{"progress": 0}]
    aggressive = CAIBridge(goal_state={"progress": 10}, personality="aggressive")
    cautious = CAIBridge(goal_state={"progress": 10}, personality="cautious")
    result_aggressive = aggressive.suggest(history, actions)[0]["progress"]
    result_cautious = cautious.suggest(history, actions)[0]["progress"]
    assert result_aggressive > result_cautious


def test_marketing_workflow_generates_marketing_plan_and_escalation():
    bridge = CAIBridge(
        goal_state={
            "session_id": "abc",
            "qualitative_targets": ["address_churn"],
        },
        workflow="marketing",
    )

    history = [
        {"role": "customer", "content": "I want to cancel if this is not fixed"}
    ]
    actions = [{}]

    result = bridge.suggest(history, actions)[0]
    assert "marketing_plan" in result
    assert any(step["goal"] == "address_churn" for step in result["marketing_plan"])
    assert any(
        command["command"] == COMMAND.ESCALATE.value for command in result["commands"]
    )


def test_support_functions_wire_connectors_and_personas():
    dispatched: list[tuple[str, dict]] = []

    class DummyConnector:
        def dispatch(self, command: str, payload: dict) -> None:
            dispatched.append((command, payload))

    loaded_personas = {}

    def persona_loader(persona_id: str):
        loaded_personas[persona_id] = {
            "id": persona_id,
            "tone": "friendly",
        }
        return loaded_personas[persona_id]

    telemetry_events = []

    def telemetry_handler(event):
        telemetry_events.append(event)

    bridge = CAIBridge(workflow="marketing")
    support = bridge.support_functions(
        connector_registry=DummyConnector(),
        persona_loader=persona_loader,
        telemetry_handler=telemetry_handler,
    )

    support["load_persona"]("advocate")
    assert "advocate" in loaded_personas

    support["session_context"]("sess-1", {"stage": "discovery"})
    assert bridge.support_functions()["session_context"]("sess-1")["metadata"][
        "stage"
    ] == "discovery"

    support["route_command"](
        {
            "command": COMMAND.SEND_EMAIL,
            "payload": {"customer_id": 42},
        }
    )
    assert dispatched == [(COMMAND.SEND_EMAIL.value, {"payload": {"customer_id": 42}})]

    support["emit_telemetry"]({"type": "manual"})
    assert telemetry_events[-1] == {"type": "manual"}


def test_cai_bridge_auto_dispatches_commands_when_configured():
    dispatched: list[tuple[str, dict]] = []

    class DummyConnector:
        def dispatch(self, command: str, payload: dict) -> None:
            dispatched.append((command, payload))

    bridge = CAIBridge(
        goal_state={
            "session_id": "sess-auto",
            "qualitative_targets": ["address_churn"],
            "auto_dispatch": True,
        },
        workflow="marketing",
    )

    bridge.support_functions(connector_registry=DummyConnector())

    history = [
        {"role": "customer", "content": "I am going to cancel unless this is resolved."}
    ]
    actions = [{}]

    result = bridge.suggest(history, actions)[0]

    assert any(cmd["command"] == COMMAND.ESCALATE.value for cmd in result["commands"])
    assert any(command == COMMAND.ESCALATE.value for command, _ in dispatched)
