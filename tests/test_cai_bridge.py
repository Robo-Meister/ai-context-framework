from caiengine.cai_bridge import CAIBridge


def test_cai_bridge_personality_changes_suggestions():
    history = [{"progress": 0}]
    actions = [{"progress": 0}]
    aggressive = CAIBridge(goal_state={"progress": 10}, personality="aggressive")
    cautious = CAIBridge(goal_state={"progress": 10}, personality="cautious")
    result_aggressive = aggressive.suggest(history, actions)[0]["progress"]
    result_cautious = cautious.suggest(history, actions)[0]["progress"]
    assert result_aggressive > result_cautious
