# HTTP API

CAIEngine exposes a FastAPI-backed HTTP surface for ingesting context, querying recent context, and interacting with goal feedback loops. This document describes the expected routes, authentication hooks, and rate limiting behavior.

## Base URL

All endpoints are served from the host and port configured for `CAIService` or `HTTPContextProvider` (for example, `http://localhost:8080`).

## Authentication

Authentication is handled by an optional `AuthHook` configured on the service. When supplied, every request is evaluated by the hook before routing. If the hook rejects the request, the service responds with `401 Unauthorized`.

## Rate limits

The service can enforce a simple per-identifier rate limit (requests per minute). Configure this via `rate_limit_per_minute` and `rate_limit_window_seconds` in `CAIService` or when constructing the HTTP app. When the rate limit is exceeded, the service responds with `429 Too Many Requests` and a JSON payload of `{ "detail": "Rate limit exceeded" }`.

## Routes

### `POST /context`

Ingest a new context payload.

**Request body**

```json
{
  "payload": {"key": "value"},
  "timestamp": "2024-01-01T00:00:00Z",
  "metadata": {"roles": ["system"]},
  "source_id": "http",
  "confidence": 1.0,
  "ttl": 3600
}
```

**Response**

```json
{
  "id": "context-id"
}
```

### `GET /context`

Query recent context within an optional time window.

**Query parameters**

- `start`: ISO 8601 timestamp (optional)
- `end`: ISO 8601 timestamp (optional)
- `scope`: context scope filter (optional)
- `data_type`: context data type filter (optional)

**Response**

```json
{
  "items": [
    {
      "id": null,
      "timestamp": "2024-01-01T00:00:00Z",
      "context": {"key": "value"},
      "roles": [],
      "situations": [],
      "content": null,
      "confidence": 1.0,
      "ocr_metadata": null
    }
  ]
}
```

### `POST /suggest`

Request goal-aware suggestions. Available only when the goal feedback loop is enabled.

**Request body**

```json
{
  "history": [],
  "current_actions": [],
  "goal_state": {"metric": 0.8}
}
```

**Response**

```json
{
  "suggestions": [
    {
      "action": "...",
      "goal_feedback": {
        "analysis": {
          "metric": {
            "goal": 0.8,
            "current": 0.6,
            "gap": 0.2,
            "baseline": 0.5,
            "trend": "up",
            "progress_ratio": 0.75
          }
        }
      }
    }
  ]
}
```

### `GET /usage`

Return token usage metrics gathered from goal feedback loop suggestions.

**Response**

```json
{
  "prompt_tokens": 1200,
  "completion_tokens": 250,
  "total_tokens": 1450
}
```

### `GET /health`

Simple health check with provider details.

**Response**

```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00Z",
  "provider": {
    "name": "caiengine.providers.http_context_provider.HTTPContextProvider",
    "backend": "caiengine.providers.memory_context_provider.MemoryContextProvider",
    "ok": true,
    "cache_size": 4
  }
}
```

### `GET /status`

Extended status endpoint exposing provider status, cache size, and goal analytics.

**Response**

```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00Z",
  "provider": {
    "name": "caiengine.providers.http_context_provider.HTTPContextProvider",
    "backend": "caiengine.providers.memory_context_provider.MemoryContextProvider",
    "ok": true,
    "cache_size": 4
  },
  "goal_analytics": {
    "history_size": 3,
    "last_suggestions": [],
    "last_analysis": {}
  }
}
```

If the goal feedback loop is not enabled, `goal_analytics` is `null`.
