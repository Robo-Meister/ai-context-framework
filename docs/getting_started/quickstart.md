# Quickstart

Get started quickly with CAIEngine using the resources below:

- **Live documentation:** [CAIEngine Docs](https://robo-meister.github.io/ai-context-framework/)
- **Contribution guide:** [docs/dev/contributing.html](../dev/contributing.html)

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

### Subscribe to context events

Each provider emits a structured event payload when new context arrives. You can
register a listener to receive status updates (for example, when new context is
published).

```python
from caiengine.providers.memory_context_provider import MemoryContextProvider

provider = MemoryContextProvider()

def on_event(event: dict) -> None:
    context = event["context"]
    print(f"Context {event['context_id']} -> {event['status']}")
    print("Payload:", context["payload"])
    print("Goal metrics:", event["goal_metrics"])

provider.subscribe_context(on_event)
provider.ingest_context(
    {"ticket": "INC-42"},
    metadata={"id": "ctx-42", "roles": ["support"], "content": "Status update"},
)
```

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

## Interact from the CLI

The `context` command-line tool ships with CAIEngine and mirrors the provider
APIs. It exposes subcommands for ingesting (`context add`) and retrieving
(`context query`) context records. Use `--provider` to select the backing
provider class; it defaults to the in-memory
`providers.memory_context_provider.MemoryContextProvider`.

### Add a context entry

Compose a JSON payload that matches your provider schema and pass optional
metadata or timestamps with the matching flags defined in `caiengine.cli`:

```bash
context --provider providers.redis_context_provider.RedisContextProvider \
  add \
  --payload '{"id": "ticket-123", "content": "Customer reported payment failure"}' \
  --metadata '{"channel": "email", "attempts": 2}' \
  --timestamp "2024-05-01T09:30:00" \
  --source-id "support-bot" \
  --confidence 0.92 \
  --ttl 3600
```

Key options:

- `--payload` (required): Raw JSON payload that will be ingested.
- `--metadata`: Additional JSON metadata, default `{}`.
- `--timestamp`: ISO 8601 timestamp; falls back to `datetime.utcnow()`.
- `--source-id`: Identifier for the producer, default `cli`.
- `--confidence`: Confidence score (string accepted by the parser, default `1.0`).
- `--ttl`: Cache retention in seconds for providers that support expirations.

### Query recent context

Retrieve context entries from the same provider by specifying an ISO timestamp
range and optional filters:

```bash
context --provider providers.redis_context_provider.RedisContextProvider \
  query \
  --start "2024-05-01T00:00:00" \
  --end "2024-05-02T00:00:00" \
  --roles "support,customer" \
  --scope "ticketing" \
  --data-type "interaction"
```

Important query arguments:

- `--start` and `--end` (required): ISO timestamps describing the query window.
- `--roles`: Comma-separated role identifiers to match.
- `--scope`: Scope string forwarded to the provider.
- `--data-type`: Data type hint for providers that differentiate entry schemas.

Results are written as JSON to standard output. Pipe the output to `jq` or
redirect it to a file for downstream processing.

### Provider configuration keys

`ConfigurablePipeline.from_dict` accepts a short provider identifier and
translates it to the underlying class from `caiengine.providers`.

| Key            | Provider class                              | Notes |
| -------------- | -------------------------------------------- | ----- |
| `memory`       | `MemoryContextProvider`                      | Ephemeral in-memory storage suitable for tests and demos. |
| `simple`       | `SimpleContextProvider`                      | Lightweight in-memory provider with peer broadcasting support. |
| `mock`         | `MockContextProvider`                        | Deterministic fixtures used by example pipelines. |
| `json` / `file`| `FileContextProvider`                        | Persists context items to a local JSON file. |
| `xml`          | `XMLContextProvider`                         | Reads structured context data from XML files. |
| `csv`          | `CSVContextProvider`                         | Streams CSV rows as context entries. |
| `ocr`          | `OCRContextProvider`                         | Wraps OCR results with metadata preservation. |
| `http`         | `HTTPContextProvider`                        | Pulls context from HTTP/REST endpoints. |
| `redis`        | `RedisContextProvider`                       | Durable Redis-backed cache with pub/sub updates. |
| `kafka`        | `KafkaContextProvider`                       | Consumes and republishes context via Kafka topics. |
| `sqlite`       | `SQLiteContextProvider`                      | Local file-based SQL storage (uses SQLite). |
| `mysql`        | `MySQLContextProvider`                       | Connects to external MySQL-compatible databases. |
| `postgres`     | `PostgresContextProvider`                    | PostgreSQL connector (alias: `postgresql`). |

All providers accept keyword arguments under `provider.args` that match their
constructor signatures. Durable backends (Redis, Kafka, and the SQL options)
require the corresponding optional extras to be installed.
