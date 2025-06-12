from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import SimpleGoalFeedbackStrategy


def test_goal_feedback_loop_basic():
    strategy = SimpleGoalFeedbackStrategy()
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 10})
    history = [{"progress": 0}]
    actions = [{"progress": 0}]
    suggested = loop.suggest(history, actions)
    assert isinstance(suggested, list)
    assert suggested[0]["progress"] == 5


def test_goal_feedback_loop_empty_history():
    strategy = SimpleGoalFeedbackStrategy()
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 10})
    suggested = loop.suggest([], [{"progress": 0}])
    assert suggested[0]["progress"] == 5


def test_goal_feedback_loop_multiple_actions():
    strategy = SimpleGoalFeedbackStrategy()
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 10})
    history = [{"progress": 4}]
    actions = [{"progress": 2}, {"progress": 6}]
    suggested = loop.suggest(history, actions)
    assert len(suggested) == 2
    assert all(act["progress"] == 7 for act in suggested)


def test_goal_feedback_loop_non_numeric_goal():
    strategy = SimpleGoalFeedbackStrategy()
    loop = GoalDrivenFeedbackLoop(
        strategy, goal_state={"progress": 10, "mood": "happy"}
    )
    history = [{"progress": 0, "mood": "sad"}]
    actions = [{"progress": 0, "mood": "sad"}]
    suggested = loop.suggest(history, actions)
    assert suggested[0]["progress"] == 5
    assert suggested[0]["mood"] == "sad"



def test_goal_feedback_loop_set_goal_state():
    strategy = SimpleGoalFeedbackStrategy()
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 4})
    history = [{"progress": 0}]
    actions = [{"progress": 0}]
    assert loop.suggest(history, actions)[0]["progress"] == 2
    loop.set_goal_state({"progress": 10})
    assert loop.suggest(history, actions)[0]["progress"] == 5
