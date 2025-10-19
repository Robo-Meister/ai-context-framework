# Quickstart

This guide shows how to install CAIEngine from PyPI, enable the optional
integrations, and run a minimal decision pipeline end-to-end.

## Install from PyPI

CAIEngine is published as [`caiengine`](https://pypi.org/project/caiengine/).
Install the base package into a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install caiengine
```

The package exposes extras for common infrastructure. Combine them as needed:

| Extra     | Installs | Use when you need |
|-----------|----------|-------------------|
| `redis`   | `redis`  | Redis-backed context streaming and pub/sub fan-out. |
| `kafka`   | `kafka-python` | Kafka ingestion and feedback channels. |
| `storage` | `mysql-connector-python`, `psycopg2-binary` | SQL persistence via MySQL or PostgreSQL providers. |

Install with pip’s bracket syntax, for example:

```bash
pip install caiengine[redis]
# Multiple extras can be combined
pip install caiengine[redis,kafka,storage]
```

## Configure optional providers

Each provider accepts keyword arguments that mirror its constructor. The most
common settings are shown below.

### Redis

```python
from caiengine.providers.redis_context_provider import RedisContextProvider

provider = RedisContextProvider(
    redis_url="redis://localhost:6379/0",
    key_prefix="context:",
)
```

The provider connects to the configured Redis instance, subscribes to the
`context:new` channel, and publishes ingested updates to listeners.

### Kafka

```python
from caiengine.providers.kafka_context_provider import KafkaContextProvider

provider = KafkaContextProvider(
    topic="context-events",
    bootstrap_servers="kafka:9092",
    group_id="cai-context",
    publish_topic="context-out",
    feedback_topic="context-feedback",
)
```

The Kafka provider consumes JSON payloads from `topic`, caches them in-memory,
and (optionally) mirrors the processed context back to `publish_topic` or a
separate `feedback_topic` for downstream workers.

### SQL storage

Install the `storage` extra to use the relational providers:

```bash
pip install caiengine[storage]
```

Then point the pipeline at the matching provider class. For example, the
PostgreSQL provider accepts a standard DSN string:

```python
from caiengine.providers.postgres_context_provider import PostgresContextProvider

provider = PostgresContextProvider(
    dsn="postgresql://user:password@localhost:5432/caiengine",
)
```

MySQL and SQLite providers follow a similar pattern. See the module docstrings
in `caiengine.providers` for the full argument lists.

## Run a decision pipeline

The `ConfigurablePipeline` wraps context ingestion, policy filtering, trust
scoring, and goal feedback in a single object. The snippet below loads a batch
of context entries from memory, evaluates them with the simple policy, and asks
the goal loop for suggestions.

```python
from caiengine.pipelines.configurable_pipeline import ConfigurablePipeline

CONFIG = {
    "provider": {"type": "memory", "args": {}},
    "candidates": [
        {"id": "workflow:triage", "priority": 0.7},
        {"id": "workflow:escalate", "priority": 0.3},
    ],
    "policy": "simple",
    "trust_weights": {"roles": 0.6, "situations": 0.3, "content": 0.1},
    "feedback": {
        "type": "goal",
        "goal_state": {"response_time": "<5m", "customer_tone": "supportive"},
        "one_direction_layers": ["response_time"],
    },
}

pipeline = ConfigurablePipeline.from_dict(CONFIG)

batch = [
    {
        "id": "ticket-123",
        "roles": ["support", "customer"],
        "situations": ["priority:high", "tier:1"],
        "content": "Customer reported payment failure",
        "context": {"channel": "email", "attempts": 2},
    }
]

results = pipeline.run(batch)
for item in results:
    print(item)
```

Running the script prints the categorised entry enriched with trust scores and
`goal_suggestion` feedback. Replace the in-memory provider configuration with
Redis, Kafka, or SQL options as your deployment requires.
