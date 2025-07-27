from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import PersonalityGoalFeedbackStrategy


def test_personality_aggressive():
    strategy = PersonalityGoalFeedbackStrategy(personality="aggressive")
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 10})
    result = loop.suggest([{"progress": 0}], [{"progress": 0}])
    assert result[0]["progress"] == 7.5


def test_personality_cautious():
    strategy = PersonalityGoalFeedbackStrategy(personality="cautious")
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 8})
    result = loop.suggest([{"progress": 4}], [{"progress": 4}])
    assert result[0]["progress"] == 5
