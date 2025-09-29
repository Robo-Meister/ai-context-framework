from caiengine.core.marketing_coach import AdaptiveCoach
from caiengine.parser.conversation_parser import ConversationState


def test_adaptive_coach_prioritises_friction_and_questions():
    state = ConversationState(session_id="sess-1")
    state.friction = 3
    state.open_questions = ["Can you confirm the new price?"]
    state.metrics["customer_messages"] = 3
    state.metrics["agent_messages"] = 1
    state.metrics["total_messages"] = 5
    state.last_customer_message = "I am upset about the downtime."

    plan = [
        {
            "goal": "address_churn",
            "actions": [],
        }
    ]

    tips = AdaptiveCoach().generate(state, plan)
    messages = [tip["message"] for tip in tips]
    priorities = {tip["priority"] for tip in tips}

    assert any("frustration" in message.lower() for message in messages)
    assert any("question" in message.lower() for message in messages)
    assert "high" in priorities
    assert any("personalise" in message.lower() for message in messages)
