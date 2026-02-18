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
            {"id": "route:standard", "priority": 0.4},
            {"id": "route:priority", "priority": 0.6},
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

fuser = Fuser()

fused = fuser.fuse(
    {
        "environment.camera": ["person detected near gate"],
        "device.motion": ["movement intensity: 0.82"],
        "location.zone": ["warehouse: east-wing"],
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
from caiengine.learning.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.learning.personality_goal_strategy import PersonalityGoalFeedbackStrategy

loop = GoalDrivenFeedbackLoop(
    strategy=PersonalityGoalFeedbackStrategy(
        personality={"tone": "encouraging", "detail_level": "medium"}
    )
)

feedback = loop.get_feedback(
    action={"type": "quiz_review", "quality": 0.7},
    goal={"mastery": 0.9},
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
