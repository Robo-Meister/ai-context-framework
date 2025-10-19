# CAIEngine

[![Test Suite](https://github.com/Robo-Meister/ai-context-framework/actions/workflows/tests.yml/badge.svg)](https://github.com/Robo-Meister/ai-context-framework/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/Robo-Meister/ai-context-framework/branch/main/graph/badge.svg)](https://codecov.io/gh/Robo-Meister/ai-context-framework)

A Context-Aware AI Engine for decision automation, workflow reasoning, and dynamic task orchestration.

CAIEngine (Context-Aware Intelligence Engine) provides a flexible AI orchestration layer for intelligent automation.

It enables:
- Context-driven task routing
- Real-time decision-making
- Modular integration with business workflows, robots, or services
- Event-driven execution with deep context tracing
- Support for AI model orchestration, reasoning, and suggestions

Use CAIEngine to build intelligent agents that understand *who*, *what*, *why*, and *when* — and take the right action.

Designed for modern systems that blend humans, AI, and devices.

## Overview

Modern AI systems often lack deep understanding of the context around inputs — such as time frames, roles, overlapping data sources, and situational nuances. This framework introduces a structured pipeline for:

- Fetching and streaming context data from various sources
- Removing duplicate or overlapping data intelligently
- Categorizing context by roles and scopes
- Fusing context into coherent embeddings or structured info
- Feeding fused context into AI inference engines
- Managing learning and model updates over time

This modular architecture is designed to evolve alongside AI needs, helping to reduce noise, increase relevance, and improve decision-making.

## Features

- Pluggable Context Providers: Redis, Kafka, file systems, and more
- Smart Deduplication: Basic and fuzzy matching to merge similar data
- Flexible Categorization: Group context by roles and scopes
- Sublayer Categorization: Nested layers (e.g. environment.camera) allow fine grained
  weighting and future filter selection. ``Fuser`` automatically merges these
  dot-separated categories without extra configuration
- Context Fusion: Aggregate and weigh data for downstream AI
- Customizable Trust Weights: Adjust context layer weights (role, environment, network, device, location, etc.) to fit your domain
- Context Memory (with Cache Management): Efficient reuse and invalidation of context data and history data
- Distributed Context Sync & Network Communication: Synchronize context state across nodes and trigger actions over the network. Includes `NetworkManager`, `SimpleNetworkMock`, `DistributedContextManager`, `ContextBus`, and network-aware hooks. See `docs/dev/network.html` for details.
- AI Inference & Learning Hooks: Modular integration points for custom AI logic and model updates
- Model Management: Replace, save, and load AI inference models at runtime
- Goal-Driven Feedback Loop: Nudge actions toward user-defined goals via strategies like ``SimpleGoalFeedbackStrategy`` or ``PersonalityGoalFeedbackStrategy`` for NPC traits
- Lightweight Text Embedding Utilities: Deterministic hashing-based embeddings, keyword categorisation, and similarity comparison without heavy ML dependencies

### Text Embedding Utilities

Use the helpers in `caiengine.core.text_embeddings` when you need deterministic,
dependency-light text processing. They expose a hashing-based embedder, a simple
keyword categoriser, and a high level comparer that mirrors the optional
PyTorch-powered components.

```python
from caiengine.core.text_embeddings import TextEmbeddingComparer

comparer = TextEmbeddingComparer()
comparison = comparer.compare(
    "Follow up with the new prospect",
    "Schedule a call with the sales lead",
    context_a={"notes": ["priority: high", "region: emea"]},
    context_b=["lead source: inbound"],
)

print(f"Similarity: {comparison['similarity']:.2f}")
print("Category A:", comparison["category_a"]["category"])
print("Category B:", comparison["category_b"]["category"])
```

`TextEmbeddingComparer` exposes lower-level helpers via `embed()` and
`categorize()` when you want manual control over embedding vectors or keyword
scoring. It gracefully degrades when optional dependencies such as PyTorch are
not installed, making it safe to use in lightweight deployments.

## Goal-Driven Feedback Use Cases

- **Learning & Skill Development** – Adaptive tutoring that delivers targeted feedback based on learner goals.
- **Workplace Training & Coaching** – On-the-job coaching that evaluates progress on objectives and offers actionable guidance.
- **Project Planning & Productivity** – Planning tools that track milestones and suggest adjustments when goals drift.
- **Code Review & Software Quality** – Automated review systems that assess pull requests against project goals and supply structured feedback.
- **Creative Work & Content Generation** – Writing assistants that help meet publishing goals through suggestions on tone and style.
- **Research & Data Analysis** – Tools that keep researchers aligned with hypothesis-driven objectives via methodological feedback.

## Documentation

- [Quickstart guide](docs/getting_started/quickstart.md) – install from PyPI,
  enable optional extras, and run a reference pipeline.
- [Developer hub](docs/dev/index.html) – HTML index that links to the existing
  architecture, API, and network deep dives.
- [Extending CAIEngine](docs/dev/extending.md) – checklist for authoring new
  context providers and goal strategies.
- [Theory and architecture notes](docs/theory/index.html) – deeper background
  on the design principles.

Install the optional `docs` extra to preview the site locally:

```bash
pip install caiengine[docs]
mkdocs serve
```

This serves the documentation at http://127.0.0.1:8000/ using the `mkdocs.yml`
navigation.

## Project Structure

```plaintext
.
├── LICENSE
├── README.md
├── pyproject.toml
├── setup.py
├── src/
│   └── caiengine/
│       ├── core/
│       │   ├── filters/
│       │   ├── learning/
│       │   └── vector_normalizer/
│       ├── common/
│       │   └── types/
│       ├── inference/
│       ├── interfaces/
│       ├── network/
│       ├── objects/
│       ├── parser/
│       └── providers/
├── docs/
│   ├── dev/
│   └── theory/
├── tests/
│   ├── learning/
│   ├── parser/
│   ├── vector_normalizer/
│   └── ...
├── __init__.py                    # Top-level API exposing key classes and mocks
```
## Getting Started

1. Clone the repository:

   ```bash
   git clone https://github.com/Robo-Meister/ai-context-framework.git
   cd ai-context-framework
   ```
2. *(Optional)* Create and activate a virtual environment

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Install dependencies and the package in editable mode. The helper script
   below installs everything needed for the full test suite (including the
   optional PyTorch components used by some tests).

   ```bash
   ./install_test_requirements.sh
   ```
4. Run the unit tests to verify your setup

   ```bash
   pytest
   ```

## Optional extras

Install extras during `pip install caiengine[...]` to bring in infrastructure
dependencies on demand:

- **Redis (`[redis]`)** – installs the `redis` client so you can use
  `RedisContextProvider` for pub/sub distribution. Supply
  `redis://host:port/db` URLs via the provider constructor or environment
  variables.
- **Kafka (`[kafka]`)** – installs `kafka-python` for the streaming
  `KafkaContextProvider`. Configure topics and bootstrap servers when instantiating
  the provider to mirror context events or feedback into your clusters.
- **Storage (`[storage]`)** – installs both `mysql-connector-python` and
  `psycopg2-binary`, enabling the MySQL and PostgreSQL providers. Point the
  constructors at your DSNs (e.g. `postgresql://user:pass@host/db`).

Extras can be combined, for example `pip install caiengine[redis,kafka]`. Once
installed, refer to the [Quickstart guide](docs/getting_started/quickstart.md)
for concrete configuration snippets.

### Starting the Service

Launch a small REST server exposing the `HTTPContextProvider` and goal feedback loop:

```bash
python -m caiengine.service
```

The server binds to `0.0.0.0:8080` by default. Set `CAI_ENGINE_ENDPOINT` in your application to this URL to reuse the running service instead of spawning `cai_bridge.py` repeatedly.

You can choose an alternative backend provider by supplying the class path and optional keyword arguments:

```bash
python -m caiengine.service \
  --backend caiengine.providers.sqlite_context_provider.SQLiteContextProvider \
  --backend-options '{"db_path": "./context.db"}'
```

### Environment Variables

Copy `.env.example` to `.env` and adjust the values as needed. The file includes
settings used by helpers and integration services.

- `CAI_ENGINE_ENDPOINT` – Base URL for services (like `npcAiService.js`) that
  communicate with the CAIEngine API.

### Loading Example Contexts

```python
from caiengine.core.trust_module import TrustModule

tm = TrustModule(weights={"role": 0.4, "location": 0.2, "device": 0.15, "action": 0.15, "time": 0.1})
tm.load_examples([
    {"role": 0.9, "location": 0.8, "time": 0.2, "device": 0.7, "action": 0.1},
    {"role": 0.8, "location": 0.7, "time": 0.1, "device": 0.6, "action": 0.2},
])
```

### Simple Provider Example

```python
from datetime import datetime, timedelta
from caiengine.providers.simple_context_provider import SimpleContextProvider
from caiengine.objects.context_query import ContextQuery

provider = SimpleContextProvider()
now = datetime.utcnow()
provider.ingest_context({"foo": "bar"}, timestamp=now)

query = ContextQuery(roles=[], time_range=(now - timedelta(seconds=1),
                                           now + timedelta(seconds=1)),
                      scope="", data_type="")
results = provider.get_context(query)
print(results)
```

### Fusing Context

```python
from caiengine.core.fuser import Fuser

fuser = Fuser()
categorized = {("", "", ""): results}
summary = fuser.fuse(categorized)
print(summary)
```
### Neural Keyword Categorization

Use ``NeuralKeywordCategorizer`` for lightweight categorization that combines a
neural model with deterministic keyword bootstrapping. Override the default
mapping by providing your own categories.

```python
from caiengine.core.categorizer import NeuralKeywordCategorizer

categorizer = NeuralKeywordCategorizer(
    {
        "sales": ("deal", "prospect"),
        "support": ("ticket", "bug"),
    }
)

item = {"content": "Investigating a ticket for a high-value prospect"}
result = categorizer.categorize(item)
print(result["category"], result["confidence"])
```

### Neural Embedding Categorization

For richer semantic matching initialise ``NeuralEmbeddingCategorizer`` with a
handful of example phrases per category.  The categorizer builds prototype
embeddings and returns softmax-normalised confidences without any additional
training.

```python
from caiengine.core.categorizer import NeuralEmbeddingCategorizer

categorizer = NeuralEmbeddingCategorizer(
    {
        "sales": ("Closing a deal", "Following up with a prospect"),
        "support": ("Investigating a ticket", "Escalating a customer bug"),
    }
)

item = {"content": "Working on an urgent ticket for a key customer"}
result = categorizer.categorize(item)
print(result["category"], result["confidence"])
```

### Configurable Pipeline

The `ConfigurablePipeline` ties providers, policies and optional feedback loops
into a single object. Simply provide a configuration dictionary and run a batch
of context items:

```python
from caiengine.pipelines.configurable_pipeline import ConfigurablePipeline
from datetime import datetime

config = {
    "provider": {"type": "memory"},
    "candidates": [
        {"category": "foo", "context": {"foo": "bar"}, "base_weight": 1.0}
    ],
    "feedback": {"type": "goal", "goal_state": {"progress": 10}},
}

pipeline = ConfigurablePipeline.from_dict(config)
data = [{
    "timestamp": datetime.utcnow(),
    "context": {"foo": "bar"},
    "content": "example"
}]
result = pipeline.run(data)
```

   
## Contributing

We welcome contributions of all kinds — feature ideas, bug fixes, documentation improvements, tests, or examples.

Please fork the repo, create a feature branch, and open a pull request. Use issues for discussion and tracking.

For an outline of ongoing development plans and upcoming features, see [docs/dev/TECHNICAL_ROADMAP.md](docs/dev/TECHNICAL_ROADMAP.md).

## License

MIT License — see LICENSE file.
