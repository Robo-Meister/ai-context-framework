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


def test_conversation_parser_extracts_entities_slots_and_discourse():
    parser = ConversationParser()
    session_id = "sess-entities"
    history = [
        {"role": "customer", "content": "Hi, I'm Alice from Acme Corp. My email is alice@example.com."},
        {
            "role": "agent",
            "content": "Hi Alice, thanks for sharing. What issue are you seeing with the analytics dashboard?",
        },
        {
            "role": "customer",
            "content": "The analytics dashboard crashes on login. It happens every morning at 9am.",
        },
        {"role": "agent", "content": "Got it. We'll involve engineering on the dashboard issue."},
        {
            "role": "customer",
            "content": "Also, the price needs to stay at $99 per month for our contract.",
        },
    ]

    state = parser.parse(session_id, history)

    # Entity recognition aggregates person, company, and contact details
    assert "alice@example.com" in state.entities.get("email", set())
    assert any(name.startswith("Alice") for name in state.entities.get("person", set()))
    assert any(company.startswith("Acme") for company in state.entities.get("company", set()))

    # Slot filling identifies price commitments and the main issue being discussed
    assert any(value.startswith("$99") for value in state.slots.get("price", set()))
    assert any("dashboard" in issue.lower() for issue in state.slots.get("issue", set()))

    # Discourse tracking links pronouns back to the referenced topic
    pronoun_links = state.discourse.get("pronoun_links", [])
    assert any("dashboard" in link["entity"].lower() for link in pronoun_links)
