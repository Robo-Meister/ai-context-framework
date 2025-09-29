# Goal-Driven Feedback Loop

Client applications often need to steer actions toward a target without pausing for user input. The goal-driven feedback loop can run as a lightweight background task to nudge progress quietly.

## Background Worker
Run the loop inside a background worker, service worker, or scheduled task. The worker should periodically poll for new actions or subscribe to an event stream.

## State Tracking
Persist the current goal state and any progress metrics in storage accessible by the worker (memory, local database, etc.). Update this state whenever goals change so the loop can compare new actions against the latest target.

## Event-Driven Updates
When a new action appears, send it to the worker through a queue or message channel. The worker computes suggestions only when history or goal state changes, limiting needless work.

## Suggestion Logic
Instantiate `GoalDrivenFeedbackLoop` with a strategy such as `SimpleGoalFeedbackStrategy` or `PersonalityGoalFeedbackStrategy`. Call `suggest_actions` with the current history and new actions to receive nudges toward the goal state.

## Example

```python
from time import sleep
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import SimpleGoalFeedbackStrategy

loop = GoalDrivenFeedbackLoop(SimpleGoalFeedbackStrategy(), goal_state={"progress": 10})
history: list[dict] = []

def worker():
    while True:
        new_actions = fetch_new_actions()
        if new_actions:
            suggestion = loop.suggest_actions(history, new_actions)
            deliver(suggestion)
            history.extend(new_actions)
        sleep(5)
```

This pattern keeps the loop running quietly in the background and only surfaces suggestions when the goal or action history changes.
