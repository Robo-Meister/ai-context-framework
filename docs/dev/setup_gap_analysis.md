# Setup Gap Analysis

This note captures a quick review of the current CAIEngine implementation and
highlights the most visible gaps that still need work before the "context-aware
automation" goal described in the README feels production-ready.

## Current strengths

* The `ConfigurablePipeline` already assembles categorisation, deduplication,
  optional policy filtering, trust scoring, and a goal-feedback loop. The
  component wiring is clear and keeps hooks for analytics via the
  `AuditLogger`.【F:src/caiengine/pipelines/configurable_pipeline.py†L8-L107】【F:src/caiengine/common/audit_logger.py†L1-L27】
* Goal-tracking primitives exist, including the reusable
  `GoalDrivenFeedbackLoop` and the simple nudging strategy. These already add
  lightweight analytics (trend, progress ratio) when suggestions are produced
  so downstream clients can show "why" a recommendation was made.【F:src/caiengine/core/goal_feedback_loop.py†L23-L144】【F:src/caiengine/core/goal_strategies/simple_goal_strategy.py†L1-L32】
* The HTTP service exposes ingestion, retrieval, goal suggestions, and token
  usage accounting, giving us an end-to-end integration touchpoint for demos and
  tests.【F:src/caiengine/service.py†L1-L91】【F:src/caiengine/providers/http_context_provider.py†L1-L91】

## Notable gaps against the setup goal

1. **Provider reach and persistence.** `ConfigurablePipeline` can only build
   pipelines backed by in-memory or file/SQL-lite providers; the richer options
   already implemented in `caiengine.providers` (Redis, Kafka, Postgres, HTTP)
   are not wired into the factory map. That limits any multi-node or durable
   setup described in the README and Roadmap. Extend `_PROVIDER_MAP` so these
   storage and streaming backends are selectable from configuration.【F:src/caiengine/pipelines/configurable_pipeline.py†L10-L41】【F:src/caiengine/providers/__init__.py†L5-L33】
2. **HTTP surface area and resilience.** The current `HTTPContextProvider` and
   `CAIService` run on Python's basic `HTTPServer` without auth, paging, error
   reporting, or lifecycle health checks. There is no rate limiting, retry
   guidance, or schema validation before data is written into memory. A thin
   ASGI/WSGI layer (FastAPI, Starlette) with request schemas would give us the
   production hardening implied in the setup goal.【F:src/caiengine/service.py†L1-L91】【F:src/caiengine/providers/http_context_provider.py†L1-L91】
3. **Durable history for goal feedback.** The goal loop keeps all history and
   baselines in RAM and resets them whenever the caller sends a non-empty
   history payload. There is no persistence or eviction policy, so any restart
   loses momentum tracking and long-running services risk unbounded growth.
   Persisting the history (e.g. via the provider or a lightweight store) and
   adding size/age limits would let the goal analytics survive restarts and
   scale beyond short demos.【F:src/caiengine/core/goal_feedback_loop.py†L32-L120】
4. **Token accounting visibility.** `TokenUsageTracker` aggregates usage but the
   service only exposes a global counter. Pipelines never log usage through the
   audit logger, making it hard to align resource consumption with specific
   context batches. Surfacing usage events (e.g. audit records per call or
   provider attribution) would help keep costs transparent when orchestrating
   multiple models.【F:src/caiengine/inference/token_usage_tracker.py†L1-L51】【F:src/caiengine/pipelines/configurable_pipeline.py†L89-L111】
5. **Cache policy hooks.** The in-memory provider stores everything until a TTL
   expires, but ingestion never forwards caller-supplied TTL values and there is
   no pruning strategy for stale context. Wiring TTL through the HTTP interface
   and surfacing cache invalidation hooks would keep the context graph fresh in
   persistent deployments.【F:src/caiengine/providers/http_context_provider.py†L1-L91】【F:src/caiengine/providers/memory_context_provider.py†L1-L55】【F:src/caiengine/core/cache_manager.py†L1-L34】

## Suggested next steps

1. Expand the pipeline factory to expose the full provider catalogue and create
   smoke tests that exercise at least one durable backend (SQLite/Redis).
2. Replace the bespoke HTTP server with a framework that gives us structured
   validation, middleware, and async concurrency; document auth expectations in
   the API docs.
3. Externalise goal-loop state (history + baselines) and add retention limits so
   analytics stay meaningful during long runs.
4. Emit token-usage audit events per inference call and link them with the
   provider/category metadata already present in pipeline results.
5. Thread TTL/retention hints through ingestion APIs and document recommended
   cache policies for different deployment tiers (demo vs production).

These changes close the biggest gaps between the current codebase and the
project's stated goal of reliable context-aware automation.
