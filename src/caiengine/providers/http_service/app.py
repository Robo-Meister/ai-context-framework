"""Shared FastAPI application factory and models for CAIEngine services."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Deque, Dict, Iterable, List

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse

from caiengine.common.token_usage import TokenCounter
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.objects.context_query import ContextQuery

AuthDecision = Response | Dict[str, Any] | bool | None
AuthHook = Callable[[Request], Awaitable[AuthDecision] | AuthDecision]
ErrorHandler = Callable[
    [Exception, Request], Awaitable[Response | Dict[str, Any] | None] | Response | Dict[str, Any] | None
]
RateLimitIdentifier = Callable[[Request], Awaitable[str] | str]


class AuthHookMiddleware:
    """Invoke an authentication hook before processing requests."""

    def __init__(self, app: FastAPI, hook: AuthHook):
        self.app = app
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


class ErrorHandlingMiddleware:
    """Catch unhandled exceptions and translate them into JSON responses."""

    def __init__(
        self,
        app: FastAPI,
        handler: ErrorHandler | None = None,
        include_details: bool = False,
    ):
        self.app = app
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


class RateLimitMiddleware:
    """Apply a simple in-memory rate limit per identifier."""

    def __init__(
        self,
        app: FastAPI,
        limit: int,
        window_seconds: float,
        identifier: RateLimitIdentifier | None = None,
    ):
        self.app = app
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


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid datetime value: {value!r}") from exc


@dataclass
class ContextIngestionRequest:
    payload: Dict[str, Any]
    timestamp: datetime | None = None
    metadata: Dict[str, Any] | None = None
    source_id: str = "http"
    confidence: float = 1.0
    ttl: int | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextIngestionRequest":
        if "payload" not in data:
            raise ValueError("payload is required")
        payload = data.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a mapping")
        return cls(
            payload=dict(payload),
            timestamp=_parse_datetime(data.get("timestamp")),
            metadata=data.get("metadata"),
            source_id=data.get("source_id", "http"),
            confidence=float(data.get("confidence", 1.0)),
            ttl=data.get("ttl"),
        )


@dataclass
class ContextIngestionResponse:
    id: str


@dataclass
class ContextRecord:
    id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)
    roles: List[str] = field(default_factory=list)
    situations: List[str] = field(default_factory=list)
    content: Any | None = None
    confidence: float = 1.0
    ocr_metadata: Dict[str, Any] | None = None

    @classmethod
    def from_mapping(cls, data: Any) -> "ContextRecord":
        mapping = dict(data)
        timestamp = _parse_datetime(mapping.get("timestamp")) or datetime.utcnow()
        return cls(
            id=mapping.get("id"),
            timestamp=timestamp,
            context=dict(mapping.get("context", {})),
            roles=list(mapping.get("roles", [])),
            situations=list(mapping.get("situations", [])),
            content=mapping.get("content"),
            confidence=float(mapping.get("confidence", 1.0)),
            ocr_metadata=mapping.get("ocr_metadata"),
        )


@dataclass
class ContextQueryResponse:
    items: List[ContextRecord]


@dataclass
class GoalSuggestionRequest:
    history: List[Dict[str, Any]] = field(default_factory=list)
    current_actions: List[Dict[str, Any]] = field(default_factory=list)
    goal_state: Dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoalSuggestionRequest":
        return cls(
            history=list(data.get("history", [])),
            current_actions=list(data.get("current_actions", [])),
            goal_state=data.get("goal_state"),
        )


@dataclass
class GoalSuggestionResponse:
    suggestions: List[Dict[str, Any]]


@dataclass
class TokenUsageResponse:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


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

    @app.post("/context", response_model=ContextIngestionResponse)
    async def ingest_context(request: ContextIngestionRequest) -> ContextIngestionResponse:
        try:
            context_id = provider.ingest_context(
                request.payload,
                timestamp=request.timestamp,
                metadata=request.metadata,
                source_id=request.source_id,
                confidence=request.confidence,
                ttl=request.ttl,
            )
        except Exception as exc:  # noqa: BLE001
            svc_logger.exception("Context ingestion failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        return ContextIngestionResponse(id=context_id)

    @app.get("/context", response_model=ContextQueryResponse)
    async def fetch_context(
        start: datetime | None = Query(default=None, description="Start of the time window."),
        end: datetime | None = Query(default=None, description="End of the time window."),
        scope: str = Query(default="", description="Context scope filter."),
        data_type: str = Query(default="", description="Context data type filter."),
    ) -> ContextQueryResponse:
        start_dt = start or datetime.min
        end_dt = end or datetime.utcnow()
        query = ContextQuery(roles=[], time_range=(start_dt, end_dt), scope=scope, data_type=data_type)
        try:
            raw_records = provider.get_context(query)
        except Exception as exc:  # noqa: BLE001
            svc_logger.exception("Context retrieval failed")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        items = [ContextRecord.from_mapping(record) for record in raw_records]
        return ContextQueryResponse(items=items)

    if include_goal_routes:
        if feedback_loop is None:
            raise ValueError("feedback_loop must be provided when include_goal_routes is True")
        if token_counter is None:
            raise ValueError("token_counter must be provided when include_goal_routes is True")

        @app.post("/suggest", response_model=GoalSuggestionResponse)
        async def suggest_actions(request: GoalSuggestionRequest) -> GoalSuggestionResponse:
            if request.goal_state is not None:
                feedback_loop.set_goal_state(request.goal_state)
            suggestions = feedback_loop.suggest(request.history, request.current_actions)
            for suggestion in suggestions:
                usage = suggestion.get("usage") if isinstance(suggestion, dict) else None
                if usage:
                    token_counter.add(usage)
            return GoalSuggestionResponse(suggestions=suggestions)

        @app.get("/usage", response_model=TokenUsageResponse)
        async def usage() -> TokenUsageResponse:
            usage_payload = token_counter.as_dict()
            return TokenUsageResponse(**usage_payload)

    return app
