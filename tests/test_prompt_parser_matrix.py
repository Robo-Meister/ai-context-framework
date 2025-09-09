from caiengine.parser.prompt_parser import PromptParser


def test_parse_to_matrix():
    parser = PromptParser()
    ctx, matrix = parser.parse_to_matrix("user is happy at home in the morning")
    assert ctx["time"] == "morning"
    assert ctx["space"] == "around the house"
    assert ctx["role"] == "user"
    assert ctx["mood"] == "happy"
    assert len(matrix) == 9

