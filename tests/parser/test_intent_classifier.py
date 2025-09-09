from caiengine.parser.intent_classifier import IntentClassifier


def test_intent_classifier_segments_and_classifies():
    clf = IntentClassifier()
    message = "What is the price? I want to buy now. I have a problem with my order."
    result = clf.parse(message)
    assert result[0]["intent"] == "question"
    assert result[0]["funnel_stage"] == "awareness"
    assert result[1]["intent"] == "purchase"
    assert result[1]["funnel_stage"] == "conversion"
    assert result[2]["intent"] == "support"
    assert result[2]["funnel_stage"] == "retention"
