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


def test_goal_feedback_loop_directional_prevents_backward():
    strategy = SimpleGoalFeedbackStrategy(one_direction_layers=["time"])
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"time": 0})
    history = [{"time": 5}]
    actions = [{"time": 5}]
    suggested = loop.suggest(history, actions)
    assert suggested[0]["time"] == 5


def test_goal_feedback_loop_directional_forward():
    strategy = SimpleGoalFeedbackStrategy(one_direction_layers=["time"])
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"time": 10})
    history = [{"time": 5}]
    actions = [{"time": 5}]
    suggested = loop.suggest(history, actions)
    assert suggested[0]["time"] == 7.5

def test_goal_feedback_loop_randomized_batch():
    strategy = SimpleGoalFeedbackStrategy()
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 100})
    history = [{"progress": i} for i in range(100)]
    actions = [{"progress": i} for i in range(100)]
    suggested = loop.suggest(history, actions)
    assert len(suggested) == len(actions)
    expected = history[-1]["progress"] + (100 - history[-1]["progress"]) * 0.5
    assert all(act["progress"] == expected for act in suggested)


def test_goal_feedback_loop_persists_history():
    strategy = SimpleGoalFeedbackStrategy()
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 10})
    loop.suggest([{"progress": 4}], [{"progress": 4}])
    # When history is omitted the loop should reuse the tracked history.
    suggestions = loop.suggest([], [{"progress": 4}])
    assert suggestions[0]["progress"] == 7


def test_goal_feedback_loop_generates_analysis_metadata():
    strategy = SimpleGoalFeedbackStrategy()
    loop = GoalDrivenFeedbackLoop(strategy, goal_state={"progress": 10})
    history = [{"progress": 2}, {"progress": 4}]
    suggestions = loop.suggest(history, [{"progress": 4}])
    analysis = loop.last_analysis
    assert "progress" in analysis
    progress_metric = analysis["progress"]
    assert progress_metric["goal"] == 10
    assert progress_metric["current"] == 4
    assert progress_metric["gap"] == 6
    assert progress_metric["trend"] == "toward_goal"
    assert 0.0 <= progress_metric["progress_ratio"] <= 1.0
    assert suggestions[0]["goal_feedback"]["analysis"]["progress"]["gap"] == 6
