# Extending CAIEngine

The core architecture is intentionally modular so that you can introduce new
context sources and goal-driven behaviours without rewriting pipelines. Review
the diagrams in [`architecture.html`](architecture.html) and the class tables on
the [developer hub](index.html) to understand how providers, feedback loops, and
pipelines compose—their relationships are reflected in those visuals.

## Build a custom context provider

Context providers transform external data into `ContextData` objects and feed
them into the pipelines. Existing implementations live under
`caiengine.providers` and typically inherit from two helper classes:

- `BaseContextProvider` (`src/caiengine/providers/base_context_provider.py`)
  implements subscriber management and peer broadcasting.
- `ContextProvider` (`src/caiengine/interfaces/context_provider.py`) supplies
  trust-weight calculations so downstream modules can score the completeness of
  each context payload.

Follow this checklist when creating your own provider:

1. **Inherit from `BaseContextProvider`.** Add any optional mixins you need
   (e.g. extend `ContextProvider` when trust weighting is required).
2. **Map incoming records to `ContextData`.** Construct instances from
   `caiengine.objects.context_data.ContextData` so the rest of the engine can
   reason about timestamps, confidence, roles, and situations uniformly.
3. **Expose ingestion hooks.** Provide `ingest_context`/`fetch_context` methods
   that convert raw payloads into `ContextData`. Look at
   `RedisContextProvider` and `KafkaContextProvider` under
   `src/caiengine/providers/` for examples of streaming integrations.
4. **Broadcast new context.** Call `self.publish_context(context_data)` after
   each ingestion so subscribers (pipelines, distributed peers, audits) receive
   updates immediately.
5. **Register with helpers.** If you want your provider to work with
   `ConfigurablePipeline.from_dict`, add it to the `_PROVIDER_MAP` in
   `src/caiengine/pipelines/configurable_pipeline.py`.
6. **Document required extras.** If the provider needs third-party packages,
   declare them under `[project.optional-dependencies]` in `pyproject.toml` and
   mention the extra in the docs so users install it with `pip install caiengine[extra]`.

## Create a goal feedback strategy

Goal strategies steer the `GoalDrivenFeedbackLoop` toward a desired state. The
loop calls `suggest_actions` with a history of outcomes, the candidate actions
returned by the pipeline, and the structured goal definition.

Start from the `GoalFeedbackStrategy` interface
(`src/caiengine/interfaces/goal_feedback_strategy.py`) and implement the
`suggest_actions` method. Use the existing strategies for inspiration:

- `SimpleGoalFeedbackStrategy` (`src/caiengine/core/goal_strategies/simple_goal_strategy.py`)
  applies rule-based nudges by reading `one_direction_layers` weights.
- `PersonalityGoalFeedbackStrategy`
  (`src/caiengine/core/goal_strategies/personality_goal_strategy.py`) layers
  persona traits on top of the base heuristics.
- The experimental `MarketingGoalFeedbackStrategy`
  (`src/caiengine/experimental/goal_strategies/marketing_goal_strategy.py`)
  demonstrates a richer scoring model that tracks campaign metrics over time.

When designing a new strategy:

1. **Define your goal schema.** Decide which keys in the `goal_state` payload you
   require (e.g. tone, latency, risk scores) and document them.
2. **Normalise inputs.** Ensure the history and action dictionaries are cleaned
   before comparison—strategies often calculate averages or deltas.
3. **Return actionable feedback.** Match the structure used by the pipelines:
   return a list aligned with the incoming `current_actions`, optionally adding
   fields such as `confidence`, `next_step`, or `target_delta`.
4. **Test with the loop.** Instantiate `GoalDrivenFeedbackLoop` with your
   strategy and verify it works with the sample pipelines in
   [`docs/getting_started/quickstart.md`](../getting_started/quickstart.md).

Link your strategy in the developer docs or README so users know which extra (if
any) they must install. For complex behaviours you can also provide diagrams or
state machines alongside the existing architecture visuals.
