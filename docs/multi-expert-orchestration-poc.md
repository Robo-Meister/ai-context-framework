# Multi-Expert Orchestration PoC

This PoC shows how CAIEngine can route a request through multiple small experts
with budgeted context packets and optional adaptive routing.

## Run

```bash
python simulation/poc_multi_expert.py
```

The script prints:

- selected and omitted context layers,
- chosen experts,
- confidence scores,
- final output payload,
- workflow graph JSON round-trip output.

## Layer naming tip (abstraction depth)

The PoC now uses layer names that encode specificity:

- `goal.meal` (general intent),
- `goal.meal.constraints` (deeper constraints),
- `retrieved.items` (broad observations),
- `retrieved.items.pantry` / `retrieved.items.calendar` (deeper observations).

This makes it easy to tune how much detail reaches experts by only changing
budget fields.

## Budget tuning behavior

Criterion 2 compares:

- a tight budget (small `max_layers` / `max_chars`) that tends to pass mostly
  higher-level layers, and
- a roomy budget that can include deeper constraint and observation layers.

Use this as a proxy for "reasoning depth" in prompt assembly before introducing
a full GoalGraph executor.

## Portable workflow graph payloads

Criterion 4 demonstrates storing a workflow graph as JSON using
`GoalGraph.to_dict()` / `GoalGraph.from_dict()`.

That keeps graphs layered and portable in the same spirit as the event context
standard, and prepares artifacts for later execution when a graph executor is
added.

## What this demonstrates

1. Request metadata can change expert selection.
2. Context packet budgets (`max_layers`, `max_chars`) change selected layers.
3. Reward feedback can improve routing when using `EpsilonGreedyRoutingPolicy`.

## What is still missing for a full workflow graph

- GoalGraph executor for walking nodes, executing tools/experts, and persisting intermediates.
- Automatic layer selection derived from graph steps and expert requirements.
- Dynamic expert lifecycle support (load/swap from model bundles).
- Evaluation harness with domain scenarios, rewards, and regression checks.
