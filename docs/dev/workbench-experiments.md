# CAIEngine Workbench experiments (development only)

The optional experimental HTTP surface exposes **real CAIEngine primitives**
through bounded, synthetic, ephemeral previews. It is designed for the
`context_engine_client` ContextWorkbench UI, not for live agent orchestration.

## Enable locally

Set both variables **on the CAIEngine service only**:

```sh
export CAI_EXPERIMENTS_ENABLED=true
export CAI_EXPERIMENTS_TOKEN='generate-a-long-random-local-token'
python -m caiengine.service --host 127.0.0.1 --port 8081 --rate-limit 30
```

Experimental routes are **not registered** if the flag is disabled or the
token is missing. An enabled request requires the
`X-Cai-Experiments-Token` HTTP header; do not put this token in a browser or
a public URL. Configure a protected server-side ContextWorkbench proxy with
the same token. Use localhost, network-level restrictions and authentication
for that proxy. Do **not** publish these routes unauthenticated to the Internet.

## Available routes

- `GET /experimental/capabilities`: active, isolated features.
- `POST /experimental/goal-loop/preview`: JSON
  `{ "goal_state": {"progress": 1}, "history": [{"progress": 0.2}],
  "current_actions": [{"progress": 0.3}] }`.
  Uses a fresh `GoalDrivenFeedbackLoop(SimpleGoalFeedbackStrategy)` and returns
  suggestions, analysis, history size and debug metadata.
- `POST /experimental/goal-graph/preview`: JSON with
  `nodes: [{id,type,label,metadata?}]`, `edges: [{source,target,label?}]`,
  optional `root_goal`. Uses `GoalGraph.from_dict` and
  `GoalGraph.subgraph_for`; returns serialized graph and reachable subset.
  Valid node types: GOAL, DECISION, TOOL, EXPERT, CONTEXT_LAYER.
- `POST /experimental/network/preview`: JSON with
  `nodes: [{id,capabilities?,drivers?,apps?}]`,
  `edges: [{source,target,weight?}]`, and
  `requirements: {capabilities?,drivers?,apps?}`.
  Uses `AgentNetwork`, `NodeRegistry`, `NodeManager`,
  `CapabilityRegistry`, `MeshDispatcher`, and `SimpleNetworkMock` to
  return match candidates, mock dispatch outcome, adjacency and telemetry.

Payloads are limited to 32 KiB, goal graphs to 60 nodes/120 edges, agent
networks to 30 nodes/80 edges, loop history to 30 entries and current
actions to 20. Nothing is sent to real RoboID addresses and no context,
registries, agents or workflow state is persisted. The demo does **not**
call the existing stateful `/suggest` route.

These endpoints are instrumentation of existing canonical implementations,
**not** a new production AI graph engine or a claim that a local preview
represents a full production dispatch. Debug payloads contain synthetic
user-provided test data and should still be kept private.

## Tests

`pytest tests/test_workbench_previews.py tests/test_cai_service.py`

## Canonical platform alignment

No new persisted state, resource entitlements, business events, workflow
transitions, risk record, documents, communications or reporting sources.
Canonical Context Engine consumers are unchanged. The experimental surface
must stay behind deployment authorization and must not become an alternate
production dispatcher. Existing auth hook and rate-limit middleware remain
applicable. API output includes provenance/debug of which canonical classes
were used. No migrations are necessary; opt-in defaults off.
