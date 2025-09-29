from caiengine.parser.conversation_parser import ConversationParser


def test_conversation_parser_tracks_state_and_questions():
    parser = ConversationParser()
    session_id = "sess-123"
    history = [
        {"role": "customer", "content": "I am thinking about switching. What is the price?"},
        {"role": "agent", "content": "We can offer a discount and the price is $10 per seat."},
        {"role": "customer", "content": "Thanks, but I am still unhappy about the outage."},
    ]

    state = parser.parse(session_id, history[:1])
    assert state.stage in {"decision", "consideration", "retention"}
    assert state.metrics["customer_messages"] == 1
    assert state.open_questions and "price" in state.open_questions[0].lower()

    state = parser.parse(session_id, history[:2])
    assert state.metrics["agent_messages"] == 1
    assert not state.open_questions

    state = parser.parse(session_id, history)
    assert state.metrics["total_messages"] == 3
    assert state.sentiment in {"negative", "neutral"}
    assert state.friction >= 1
    assert "friction" in state.tags
    assert state.last_customer_message.endswith("outage.")
