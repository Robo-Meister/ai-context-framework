# AI Context Framework

A modular Python framework to collect, deduplicate, categorize, fuse, and leverage contextual data for smarter AI inference — emphasizing role, time, and situation awareness.

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
- Context Fusion: Aggregate and weigh data for downstream AI
- Customizable Trust Weights: Adjust context layer weights (role, environment, network, device, location, etc.) to fit your domain
- Context Memory (with Cache Management): Efficient reuse and invalidation of context data and history data *(planned)*
- Distributed Context Sync & Network Communication: Synchronize context state across nodes, support multi-agent collaboration, and enable context-aware messaging. Basic support provided via `NetworkManager`, `SimpleNetworkMock`, and `DistributedContextManager`. See `docs/dev/network.html` for details.
- AI Inference & Learning Hooks: Modular integration points for custom AI logic and model updates

## Project Structure

```plaintext
.
├── LICENSE
├── README.md
├── pyproject.toml
├── setup.py
├── core/
│   ├── filters/
│   ├── learning/
│   └── vector_normalizer/
├── common/
│   └── types/
├── inference/
├── interfaces/
├── network/
├── objects/
├── parser/
├── providers/
├── documentation/
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
   https://github.com/Robo-Meister/ai-context-framework.git
   cd ai-context-framework
   ```
2. Create and activate virtual environment (optional but recommended)
    ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Install dependencies (to be updated)
```bash
pip install -r requirements.txt
Start by implementing your own ContextProvider or test the provided Redis provider.
```

### Loading Example Contexts

```python
from core.trust_module import TrustModule

tm = TrustModule(weights={"role": 0.4, "location": 0.2, "device": 0.15, "action": 0.15, "time": 0.1})
tm.load_examples([
    {"role": 0.9, "location": 0.8, "time": 0.2, "device": 0.7, "action": 0.1},
    {"role": 0.8, "location": 0.7, "time": 0.1, "device": 0.6, "action": 0.2},
])
```
   
## Contributing

We welcome contributions of all kinds — feature ideas, bug fixes, documentation improvements, tests, or examples.

Please fork the repo, create a feature branch, and open a pull request. Use issues for discussion and tracking.

## License

MIT License — see LICENSE file.