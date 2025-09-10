# Event Context Standard

This document defines a standard structure for representing events with
multi-layered context and trust metadata.

## Data model

* **Event**
  * `event_id`: unique identifier
  * `timestamp`: epoch seconds
  * `source`: origin system or actor
  * `payload`: raw message or data
  * `contexts`: mapping of context categories
* **ContextCategory**
  * `name`: category label such as `user`, `device`, or `environment`
  * `layers`: ordered list of context layers
* **ContextLayer**
  * `layer_id`: identifier within the category
  * `data`: arbitrary JSON-compatible payload
  * `weight`: relevance weighting (0.0–1.0)
  * `trust`: confidence score (0.0–1.0)
  * `scope`: optional scope such as `global`, `session`, or `request`
  * `parent`: optional parent layer identifier

## Distribution

Events and their context can be distributed as JSON documents. The
structure is portable across languages and can be transported via message
queues, HTTP APIs, or persisted to files. The default implementation
uses JSON for ease of inspection and interoperability.

## Persistence API

The module `caiengine.common.context_model` provides classes for the data
model and helper functions for persistence:

```python
from caiengine.common import Event, ContextCategory, ContextLayer

layer = ContextLayer(layer_id="session", data={"user": "abc"}, weight=0.8)
category = ContextCategory(name="user", layers=[layer])

event = Event(
    event_id="evt-1",
    timestamp=1710000000.0,
    source="sensor-A",
    payload={"action": "login"},
    contexts={"user": category},
)

# Save and load
path = "event.json"
event.save(path)
loaded = Event.load(path)
```

This API allows components to persist or transmit events with their
associated context in a standardized format.
