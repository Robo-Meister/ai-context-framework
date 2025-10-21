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

### Goal Feedback Loop Diagnostics

`GoalFeedbackWorker` escalates retries into exponential backoff while tagging
every failure with `attempt` and `backoff_seconds`. A follow-up debug log then
emits `backoff_remaining` while the worker sleeps. Configure your logging
pipeline to alert when those fields remain high for several cycles—this usually
means the underlying provider keeps raising and the loop is stuck.

`GoalStateTracker` and the storage backends also log when they fall back to
in-memory persistence. Treat that warning as an operational smell in
environments where resilience matters and override the backend with SQLite or
Redis in production deployments.

### Provider Error Visibility

Each context provider now emits structured errors if a subscriber callback
crashes or if ingestion fails. The records include the `subscriber_id`,
`context_id`, and backend-specific identifiers (for example, the SQLite
database path). Attach handlers with filters that forward these errors to the
same observability system as the rest of your application so that failed
downstream consumers are visible without reproducing the issue locally.

## Token Usage Telemetry

Inference engines wrapped by `TokenUsageTracker` now emit structured telemetry
for every model invocation. Pipelines created through
`ConfigurablePipeline.from_dict` automatically forward these events to the
`AuditLogger` so downstream systems can observe prompt/completion token
consumption per provider/category combination. Each audit record uses the
`token_usage` step name and provides a payload similar to:

```json
{
  "timestamp": "2024-05-12T10:15:32.123456",
  "operation": "predict",
  "provider": "memory",
  "category": "support",
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 13,
    "total_tokens": 55
  }
}
```

Attach custom listeners to `TokenUsageTracker.register_usage_listener` if you
need to ship the telemetry to additional observability sinks.

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

## Service Middleware Hooks

`CAIService` now exposes its HTTP surface through FastAPI which makes it easy to
insert cross-cutting concerns via middleware. Three lightweight middlewares are
enabled out of the box and can be tuned when the service is constructed:

| Concern        | Configuration knob | Notes |
| -------------- | ------------------ | ----- |
| Authentication | `auth_hook: Callable[[Request], Awaitable[AuthDecision] | AuthDecision]` | Hook receives the incoming `Request` and may return a `Response`, a `dict` payload, or `False` to reject the call. |
| Error handling | `error_handler: Callable[[Exception, Request], Awaitable[Response | dict] | Response | dict]`, `include_error_details: bool` | Translate exceptions into custom JSON payloads or expose the original error message when `include_error_details` is set. |
| Rate limiting  | `rate_limit_per_minute: int`, `rate_limit_window_seconds: float`, `rate_limit_identifier: Callable[[Request], Awaitable[str] | str]` | Configure the number of allowed requests per window and optionally derive a custom identifier (for example from an API key). A limit of `0` disables the middleware. |

When running from the CLI the following flags surface the same controls:

```bash
python -m caiengine.service --host 0.0.0.0 --port 8080 \
  --rate-limit 120 --rate-limit-window 60 \
  --include-error-details
```

Applications embedding the service can also inspect metrics via the `/usage`
endpoint which reports aggregated token counts from the goal feedback loop so
that traffic shaping can be correlated with model consumption.
