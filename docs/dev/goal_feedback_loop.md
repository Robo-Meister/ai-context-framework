# Goal-Driven Feedback Loop

Client applications often need to steer actions toward a target without pausing for user input. The goal-driven feedback loop can run as a lightweight background task to nudge progress quietly.

## Background Worker
Run the loop inside a background worker, service worker, or scheduled task. The worker should periodically poll for new actions or subscribe to an event stream.

Use ``GoalFeedbackWorker`` as a starting point. The worker ships with a synchronous polling hook, structured logging around
retries, and automatic persistence wiring through ``GoalStateTracker``. Provide a callable that yields events if you want the
worker to poll on every cycle; otherwise it idles and reacts to messages published on the event bus.

## State Tracking
Persist the current goal state and any progress metrics in storage accessible by the worker (memory, local database, etc.). Update this state whenever goals change so the loop can compare new actions against the latest target.

``GoalStateTracker`` stores state in memory by default and logs a warning so you know data will reset on restart. Supply
``loader`` and ``saver`` callables to plug in Redis, a database, or any other persistence tier—errors are logged and the
in-memory snapshot remains available.

## Event-Driven Updates
When a new action appears, send it to the worker through a queue or message channel. The worker computes suggestions only when history or goal state changes, limiting needless work.

``FeedbackEventBus`` offers a minimal publish/subscribe interface. It emits debug logs for each event and shields other
subscribers from exceptions raised by one handler. Swap it out for an async queue or broker when you need horizontal scale.

## Suggestion Logic
Instantiate `GoalDrivenFeedbackLoop` with a strategy such as `SimpleGoalFeedbackStrategy` or `PersonalityGoalFeedbackStrategy`. Call `suggest_actions` with the current history and new actions to receive nudges toward the goal state.

## Logging and Monitoring

Workers and providers initialise named loggers using Python's ``logging`` module. Configure logging in your application entry
point so these diagnostics reach your observability stack:

```python
import logging
import logging.config

logging.config.dictConfig(
    {
        "version": 1,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
            }
        },
        "formatters": {
            "structured": {
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
    }
)
```

The worker emits ``INFO`` entries when processing events, ``DEBUG`` logs while polling, and ``ERROR`` records whenever backoff is
triggered due to exceptions. Providers log ingestion successes, peer broadcast attempts, and file/database failures. Attach a
custom ``logging.Handler`` if you need to forward structured payloads to tools such as OpenTelemetry or Datadog.

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
