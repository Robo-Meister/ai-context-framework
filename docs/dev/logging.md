# Logging and Observability

The AI Context Framework standardises on Python's built-in `logging` module for
all observability hooks. Workers and providers create named loggers using their
fully-qualified module and class names so that deployments can selectively tune
verbosity.

## Configuring Log Levels

The framework does not install a global logging configuration. Downstream
applications are expected to configure handlers and levels at process start-up,
for example:

```python
import logging

logging.basicConfig(
    level="INFO",
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
```

To increase verbosity for a specific component you can adjust its logger name.
The goal feedback worker uses the logger name
`"caiengine.core.goal_feedback_worker.GoalFeedbackWorker"`, while context
providers follow the pattern `"<module>.<ClassName>"`.

```python
logging.getLogger("caiengine.core.goal_feedback_worker.GoalFeedbackWorker").setLevel("DEBUG")
```

## Structured Log Fields

Critical log entries add structured fields via `extra` so that centralised log
collectors can capture metadata (for example `pending_actions`,
`backoff_seconds`, or `subscriber_id`). When configuring formatters include the
field names you care about, e.g. `%(message)s pending=%(pending_actions)s`, or
use a JSON formatter to retain the structured attributes automatically.

## Hooking into External Observability

If you need to forward logs to an external sink, attach handlers to the relevant
logger:

```python
handler = logging.StreamHandler()
handler.setLevel("WARNING")
logging.getLogger("caiengine.providers.kafka_context_provider.KafkaContextProvider").addHandler(handler)
```

Handlers inherit levels from their parent logger hierarchy. Set
`propagate = False` if you want to suppress duplicate entries once a custom
handler is attached.
