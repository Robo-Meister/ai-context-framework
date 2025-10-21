# Goal-Driven Feedback Loop

Client applications often need to steer actions toward a target without pausing for user input. The goal-driven feedback loop can run as a lightweight background task to nudge progress quietly.

## Background Worker
Run the loop inside a background worker, service worker, or scheduled task. The worker should periodically poll for new actions or subscribe to an event stream.

Use the scaffold in ``GoalFeedbackWorker`` as a starting point.
TODO: implement real polling logic and persistence integration.

## State Tracking
Persist the current goal state and any progress metrics in storage accessible by the worker (memory, local database, etc.). Update this state whenever goals change so the loop can compare new actions against the latest target.

`GoalDrivenFeedbackLoop` now supports pluggable persistence providers. Pass a custom provider that implements `GoalFeedbackPersistence` when constructing the loop to persist the action history and calculated baselines into durable storage (e.g. SQLite, Redis, or a managed cache). The default provider keeps data in memory inside the current process.

```python
from caiengine.core.goal_feedback_loop import (
    GoalDrivenFeedbackLoop,
    SQLiteGoalFeedbackPersistence,
)

persistence = SQLiteGoalFeedbackPersistence("/var/lib/app/goal_feedback.db")
loop = GoalDrivenFeedbackLoop(strategy, goal_state=my_goal, persistence=persistence)
```

### Retention controls
To prevent unbounded growth, configure retention parameters when creating the loop:

* `retention_limit` trims the stored history to the most recent *N* entries.
* `retention_window` discards entries older than the supplied duration (seconds or `timedelta`).

Both policies can be combined. After pruning, baselines automatically recalculate so that analytics continue to reflect the oldest retained datapoints.

## Event-Driven Updates
When a new action appears, send it to the worker through a queue or message channel. The worker computes suggestions only when history or goal state changes, limiting needless work.

``FeedbackEventBus`` offers a minimal publish/subscribe interface.
TODO: replace with an async queue or external message broker.

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
