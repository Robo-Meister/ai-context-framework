# API Reference

This document outlines the stable public API surface of `caiengine` along with
optional extras and experimental modules. The package now performs lazy loading
of heavy components during attribute access, so importing `caiengine` keeps
startup time low while still exposing the documented entry points.

## Stable top-level symbols

Importing ``caiengine`` exposes the following stable objects via lazy loaders:

- `CacheManager`
- `AIInferenceEngine`
- `ContextPipeline`
- `FeedbackPipeline`
- `QuestionPipeline`
- `PromptPipeline`
- `ConfigurablePipeline`
- `Fuser`
- `ContextManager`
- `DistributedContextManager`
- `ContextHookManager`
- `ContextHook`
- `MemoryContextProvider`
- `KafkaContextProvider`*
- `PolicyEvaluator`
- `export_onnx_bundle`
- `load_model_manifest`
- `model_manager`
- `NetworkManager`
- `SimpleNetworkMock`
- `ContextBus`
- `NodeRegistry`
- `ModelRegistry`
- `RedisPubSubChannel`*
- `KafkaPubSubChannel`*
- `NetworkInterface`
- `GoalDrivenFeedbackLoop`
- `SimpleGoalFeedbackStrategy`
- `PersonalityGoalFeedbackStrategy`
- `GoalFeedbackWorker`
- `GoalStateTracker`
- `SQLiteGoalStateBackend`
- `RedisGoalStateBackend`*
- `FeedbackEventBus`
- `CAIBridge`
- `FileModelRegistry`
- `cli`

`__version__` is also available for compatibility. Items marked with `*`
require optional extras that are described below.

## Optional extras

Some components rely on third-party libraries that are not installed by
default. Attempting to access the corresponding symbol will raise a helpful
error unless the matching extra set is installed.

| Extra name | Symbols |
| ---------- | ------- |
| `kafka`    | `KafkaContextProvider`, `KafkaPubSubChannel` |
| `redis`    | `RedisPubSubChannel`, `RedisGoalStateBackend` |

Install extras with standard pip syntax, e.g. ``pip install caiengine[kafka]``.

## Light-weight imports

Setting the environment variable ``CAIENGINE_LIGHT_IMPORT`` restricts the
package to exposing only ``__version__`` and the ``cli`` module for minimal
CLI-focused usage. All other attributes remain accessible through their module
paths, e.g. ``from caiengine.pipelines import ContextPipeline``.

## Experimental modules

Experimental utilities have been moved under the ``caiengine.experimental``
namespace. They are not covered by the stability guarantees above and may
change without notice. Current experimental exports include:

- `caiengine.experimental.marketing_coach.AdaptiveCoach`
- `caiengine.experimental.marketing_coach.CoachingTip`
- `caiengine.experimental.goal_strategies.MarketingGoalFeedbackStrategy`

When importing ``caiengine`` these symbols are no longer re-exported at the top
level, making their experimental status explicit.

## Goal state persistence backends

`GoalStateTracker` accepts either a fully constructed backend instance or a
configuration mapping describing how to build one. This makes it easy to wire
the tracker using dependency injection containers or settings files.

Example configuration loaded from application settings::

    goal_state_backend = {"type": "sqlite", "database": "/var/app/goal_state.db"}
    tracker = GoalStateTracker(backend_config=goal_state_backend)

To integrate with Redis, provide either a pre-configured client instance or a
connection URL::

    tracker = GoalStateTracker(
        backend_config={
            "type": "redis",
            "url": "redis://localhost:6379/0",
            "key": "myapp:goal_state",
        }
    )

When using dependency injection frameworks, instantiate the backend externally
and pass it directly::

    backend = SQLiteGoalStateBackend("/var/app/goal_state.db")
    tracker = GoalStateTracker(backend=backend)
