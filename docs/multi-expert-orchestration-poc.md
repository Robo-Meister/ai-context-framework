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
- final output payload.

## What this demonstrates

1. Request metadata can change expert selection.
2. Context packet budgets (`max_layers`, `max_chars`) change selected layers.
3. Reward feedback can improve routing when using `EpsilonGreedyRoutingPolicy`.

## What is still missing for a full workflow graph

- GoalGraph executor for walking nodes, executing tools/experts, and persisting intermediates.
- Automatic layer selection derived from graph steps and expert requirements.
- Dynamic expert lifecycle support (load/swap from model bundles).
- Evaluation harness with domain scenarios, rewards, and regression checks.
