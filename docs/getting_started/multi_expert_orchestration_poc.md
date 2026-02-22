# Multi-Expert Orchestration PoC

This PoC demonstrates how `OrchestratedPipeline` can route a request through
multiple small experts instead of one large model, while using a budgeted
context packet and optional adaptive routing.

## What this PoC proves

Success criteria covered by the PoC script:

1. Changing request metadata changes which experts are selected.
2. Context packet budgets (`max_layers` / `max_chars`) change which context
   layers are included.
3. With a simple reward signal, adaptive routing (`EpsilonGreedyRoutingPolicy`)
   improves expert selection over time.
4. Workflow graphs can be stored as portable JSON payloads via
   `GoalGraph.to_dict()` / `GoalGraph.from_dict()`.

Non-goals:

- This PoC does not execute multi-step GoalGraphs.
- This PoC does not require an external LLM provider.

## Prerequisites

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .[dev]
```

## Run the PoC

```bash
python simulation/multi_expert_orchestration_poc.py
```

The script prints three sections, one for each criterion.

## How it is wired

- `OrchestratedPipeline` compiles a context packet and emits telemetry.
- `ContextPacketCompiler` applies required + optional layer selection under
  `max_layers` and `max_chars` budgets.
- `ExpertRouter` uses either:
  - `RuleBasedRoutingPolicy` for deterministic capability matching, or
  - `EpsilonGreedyRoutingPolicy` for adaptive selection based on rewards.

## Expected output cues

- Criterion 1 should print different expert lists for support vs finance
  metadata.
- Criterion 2 should show fewer layers with the tight budget than with the
  roomy budget.
- In Criterion 2, layer naming communicates abstraction depth, for example:
  - `goal.meal` (general),
  - `goal.meal.constraints` (more specific),
  - `retrieved.items` (observations),
  - `retrieved.items.pantry` and `retrieved.items.calendar` (deeper sources).
  Changing `budget.max_layers` / `budget.max_chars` should determine whether
  only broad layers or deeper layers are passed onward.
- Criterion 3 should select a baseline expert before rewards and prefer the
  higher-reward expert after repeated outcomes are recorded.
- Criterion 4 should print serialized graph JSON and confirm round-trip
  stability (`True`).
