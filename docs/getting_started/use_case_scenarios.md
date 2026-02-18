# Use Case Scenarios

This page shows practical CAIEngine examples for different scenarios. Each
scenario includes a compact snippet so you can quickly adapt it to your own
application.

## 1) Customer support triage assistant

Use this pattern when you ingest support tickets and want to route them through
a consistent policy + goal feedback pipeline.

```python
from caiengine.pipelines.configurable_pipeline import ConfigurablePipeline

pipeline = ConfigurablePipeline.from_dict(
    {
        "provider": {"type": "memory", "args": {}},
        "policy": "simple",
        "candidates": [
            {
                "category": "route:standard",
                "context": {"channel": "chat", "plan": "business"},
                "base_weight": 0.4,
            },
            {
                "category": "route:priority",
                "context": {
                    "channel": "chat",
                    "plan": "business",
                    "priority": "high",
                },
                "base_weight": 0.6,
            },
        ],
        "feedback": {
            "type": "goal",
            "goal_state": {
                "first_response": "<10m",
                "tone": "supportive",
            },
        },
    }
)

results = pipeline.run(
    [
        {
            "id": "ticket-1001",
            "roles": ["support", "customer"],
            "situations": ["priority:high"],
            "content": "Customer cannot access billing portal",
            "context": {"channel": "chat", "plan": "business"},
        }
    ]
)

print(results[0]["goal_suggestion"])
```

## 2) IoT / robotics event aggregation

Use sublayer categories to combine environment and device context before
reasoning (for example `environment.camera` and `device.motion`).

```python
from caiengine.core.fuser import Fuser
from datetime import datetime

fuser = Fuser()

fused = fuser.fuse(
    {
        ("environment", "2025-01-01T09", "camera"): [
            {
                "timestamp": datetime.fromisoformat("2025-01-01T09:00:00"),
                "content": "person detected near gate",
                "confidence": 0.96,
            }
        ],
        ("device", "2025-01-01T09", "motion"): [
            {
                "timestamp": datetime.fromisoformat("2025-01-01T09:00:03"),
                "content": "movement intensity: 0.82",
                "confidence": 0.89,
            }
        ],
        ("location", "2025-01-01T09", "zone"): [
            {
                "timestamp": datetime.fromisoformat("2025-01-01T09:00:01"),
                "content": "warehouse: east-wing",
                "confidence": 1.0,
            }
        ],
    }
)

print(fused)
```

## 3) Cross-team context sharing with Redis

Use this when multiple services need a shared context stream.

```python
from caiengine.providers.redis_context_provider import RedisContextProvider

provider = RedisContextProvider(
    redis_url="redis://localhost:6379/0",
    key_prefix="ops:",
)

provider.ingest_context(
    {"event": "shipment_delayed", "order_id": "SO-55"},
    metadata={"id": "ctx-shipment-55", "roles": ["operations"]},
)
```

## 4) Batch analysis in data workflows

Use this in periodic jobs where a static batch of context records is scored and
compared.

```python
from caiengine.core.text_embeddings import TextEmbeddingComparer

comparer = TextEmbeddingComparer()

comparison = comparer.compare(
    "Escalate churn-risk account to retention team",
    "Create proactive outreach task for at-risk customer",
    context_a={"segment": "enterprise"},
    context_b={"segment": "enterprise"},
)

print(comparison["similarity"])
print(comparison["category_a"]["category"])
```

## 5) Goal coaching for learning products

Use personality-aware feedback when your app needs coaching behaviour with
specific tone traits.

```python
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies.personality_goal_strategy import PersonalityGoalFeedbackStrategy

loop = GoalDrivenFeedbackLoop(
    strategy=PersonalityGoalFeedbackStrategy(personality="neutral"),
    goal_state={"mastery": 0.9},
)

feedback = loop.suggest(
    history=[{"mastery": 0.5}],
    current_actions=[{"type": "quiz_review", "mastery": 0.7}],
)

print(feedback)
```

## Choosing the right starting point

- Start with **Scenario 1** if you are building a business assistant.
- Start with **Scenario 2** for edge/robotics sensor fusion.
- Start with **Scenario 3** if you need distributed services.
- Start with **Scenario 4** for offline analytics workflows.
- Start with **Scenario 5** for coaching or tutoring products.

For full setup steps, see the [Quickstart](quickstart.md).
