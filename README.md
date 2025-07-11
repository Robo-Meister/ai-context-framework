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
- Goal-Driven Feedback Loop: Nudge actions toward user-defined goals via strategies like ``SimpleGoalFeedbackStrategy``

## Documentation

Developer guides live in the `docs/` directory. Open
[docs/dev/index.html](docs/dev/index.html) for usage instructions and
[docs/theory/index.html](docs/theory/index.html) for design notes.

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

You can now start implementing your own `ContextProvider` or test the built-in ones.

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
