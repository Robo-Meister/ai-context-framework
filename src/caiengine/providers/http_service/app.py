"""Shared FastAPI application factory and models for CAIEngine services."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Awaitable, Callable, Deque, Dict, Iterable, List

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from caiengine.common.token_usage import TokenCounter
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.objects.context_query import ContextQuery

AuthDecision = Response | Dict[str, Any] | bool | None
AuthHook = Callable[[Request], Awaitable[AuthDecision] | AuthDecision]
ErrorHandler = Callable[
    [Exception, Request], Awaitable[Response | Dict[str, Any] | None] | Response | Dict[str, Any] | None
]
RateLimitIdentifier = Callable[[Request], Awaitable[str] | str]


class AuthHookMiddleware(BaseHTTPMiddleware):
    """Invoke an authentication hook before processing requests."""

    def __init__(self, app: FastAPI, hook: AuthHook):
        super().__init__(app)
        self.hook = hook

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        decision = self.hook(request)
        if inspect.isawaitable(decision):
            decision = await decision
        if isinstance(decision, Response):
            return decision
        if isinstance(decision, dict):
            return JSONResponse(decision, status_code=status.HTTP_401_UNAUTHORIZED)
        if decision is False:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return await call_next(request)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and translate them into JSON responses."""

    def __init__(
        self,
        app: FastAPI,
        handler: ErrorHandler | None = None,
        include_details: bool = False,
    ):
        super().__init__(app)
        self.handler = handler
        self.include_details = include_details
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        try:
            return await call_next(request)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - propagate through JSON response
            if self.handler:
                mapped = self.handler(exc, request)
                if inspect.isawaitable(mapped):
                    mapped = await mapped
                if isinstance(mapped, Response):
                    return mapped
                if isinstance(mapped, dict):
                    return JSONResponse(mapped, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.logger.exception(
                "Unhandled service error",
                extra={"path": str(request.url.path)},
            )
            detail = str(exc) if self.include_details else "Internal server error"
            return JSONResponse(
                {"detail": detail},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a simple in-memory rate limit per identifier."""

    def __init__(
        self,
        app: FastAPI,
        limit: int,
        window_seconds: float,
        identifier: RateLimitIdentifier | None = None,
    ):
        super().__init__(app)
        self.limit = limit
        self.window = window_seconds
        self.identifier = identifier or self._default_identifier
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    @staticmethod
    async def _default_identifier(request: Request) -> str:
        if request.client:
            return request.client.host
        return "anonymous"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        if self.limit <= 0:
            return await call_next(request)
        ident = self.identifier(request)
        if inspect.isawaitable(ident):
            ident = await ident
        now = time.monotonic()
        async with self._lock:
            timestamps = self._requests[ident]
            cutoff = now - self.window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            timestamps.append(now)
        return await call_next(request)


def create_http_service_app(
    *,
    provider: Any,
    logger: logging.Logger | None = None,
    feedback_loop: GoalDrivenFeedbackLoop | None = None,
    token_counter: TokenCounter | None = None,
    auth_hook: AuthHook | None = None,
    error_handler: ErrorHandler | None = None,
    rate_limit_per_minute: int = 0,
    rate_limit_window_seconds: float = 60.0,
    include_error_details: bool = False,
    rate_limit_identifier: RateLimitIdentifier | None = None,
    include_goal_routes: bool = True,
    title: str = "CAI Engine Service",
    version: str = "1.0.0",
) -> FastAPI:
    """Create a FastAPI application exposing CAIEngine HTTP endpoints."""

    app = FastAPI(title=title, version=version)

    if error_handler or include_error_details:
        app.add_middleware(
            ErrorHandlingMiddleware,
            handler=error_handler,
            include_details=include_error_details,
        )
    if rate_limit_per_minute > 0:
        app.add_middleware(
            RateLimitMiddleware,
            limit=rate_limit_per_minute,
            window_seconds=rate_limit_window_seconds,
            identifier=rate_limit_identifier,
        )
    if auth_hook:
        app.add_middleware(AuthHookMiddleware, hook=auth_hook)

    svc_logger = logger or logging.getLogger("caiengine.http_service")

    @app.post("/context")
    async def ingest_context(request: Request) -> Dict[str, Any]:
        payload = _ensure_json_dict(request)
        context_payload = payload.get("payload")
        if not isinstance(context_payload, dict):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="payload must be an object")

        timestamp = _parse_optional_datetime(payload.get("timestamp"))
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else None
        source_id = payload.get("source_id", "http")
        confidence = _parse_optional_float(payload.get("confidence"), default=1.0, field="confidence", min_value=0.0)
        ttl = _parse_optional_int(payload.get("ttl"), field="ttl", min_value=0)

        try:
            context_id = provider.ingest_context(
                context_payload,
                timestamp=timestamp,
                metadata=metadata,
                source_id=source_id,
                confidence=confidence,
                ttl=ttl,
            )
        except Exception as exc:  # noqa: BLE001
            svc_logger.exception("Context ingestion failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        return {"id": context_id}

    @app.get("/context")
    async def fetch_context(request: Request) -> Dict[str, Any]:
        params = dict(request.query_params)
        start_dt = _parse_optional_datetime(params.get("start")) or datetime.min
        end_dt = _parse_optional_datetime(params.get("end")) or datetime.utcnow()
        scope = params.get("scope", "") or ""
        data_type = params.get("data_type", "") or ""
        query = ContextQuery(roles=[], time_range=(start_dt, end_dt), scope=scope, data_type=data_type)
        try:
            raw_records = provider.get_context(query)
        except Exception as exc:  # noqa: BLE001
            svc_logger.exception("Context retrieval failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        items = [_normalise_context_record(record) for record in raw_records]
        return {"items": items}

    if include_goal_routes:
        if feedback_loop is None:
            raise ValueError("feedback_loop must be provided when include_goal_routes is True")
        if token_counter is None:
            raise ValueError("token_counter must be provided when include_goal_routes is True")

        @app.post("/suggest")
        async def suggest_actions(request: Request) -> Dict[str, Any]:
            payload = _ensure_json_dict(request)
            history = _ensure_list_of_dict(payload.get("history", []), field="history")
            current_actions = _ensure_list_of_dict(payload.get("current_actions", []), field="current_actions")
            goal_state = payload.get("goal_state")
            if goal_state is not None and not isinstance(goal_state, dict):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="goal_state must be an object")
            if goal_state is not None:
                feedback_loop.set_goal_state(goal_state)
            suggestions = feedback_loop.suggest(history, current_actions)
            for suggestion in suggestions:
                usage = suggestion.get("usage") if isinstance(suggestion, dict) else None
                if usage:
                    token_counter.add(usage)
            return {"suggestions": suggestions}

        @app.get("/usage")
        async def usage() -> Dict[str, Any]:
            return token_counter.as_dict()

    return app


def _ensure_json_dict(request: Request) -> Dict[str, Any]:
    data = request.json()
    if not isinstance(data, dict):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Request body must be a JSON object")
    return data


def _parse_optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid datetime format") from exc
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid datetime value")


def _parse_optional_float(value: Any, *, default: float, field: str, min_value: float | None = None) -> float:
    if value is None:
        result = default
    else:
        try:
            result = float(value)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field} must be a number") from exc
    if min_value is not None and result < min_value:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field} must be >= {min_value}")
    return result


def _parse_optional_int(value: Any, *, field: str, min_value: int | None = None) -> int | None:
    if value is None:
        return None
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field} must be an integer") from exc
    if min_value is not None and result < min_value:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field} must be >= {min_value}")
    return result


def _ensure_list_of_dict(value: Any, *, field: str) -> List[Dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field} must be a list of objects")
    result: List[Dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{field} must contain only objects")
        result.append(item)
    return result


def _normalise_context_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid context record")
    normalised = dict(record)
    normalised.setdefault("id", None)
    normalised.setdefault("roles", [])
    normalised.setdefault("situations", [])
    normalised.setdefault("context", {})
    normalised.setdefault("confidence", 1.0)
    normalised.setdefault("content", None)
    normalised.setdefault("ocr_metadata", None)
    return normalised
