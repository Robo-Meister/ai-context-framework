"""Shared FastAPI application factory and models for CAIEngine services."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Awaitable, Callable, Deque, Dict, Iterable, List

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
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


class ContextIngestionRequest(BaseModel):
    payload: Dict[str, Any]
    timestamp: datetime | None = None
    metadata: Dict[str, Any] | None = None
    source_id: str = Field(default="http", description="Identifier for the data source.")
    confidence: float = Field(default=1.0, ge=0.0)


class ContextIngestionResponse(BaseModel):
    id: str


class ContextRecord(BaseModel):
    id: str | None = None
    timestamp: datetime
    context: Dict[str, Any] = Field(default_factory=dict)
    roles: List[str] = Field(default_factory=list)
    situations: List[str] = Field(default_factory=list)
    content: Any | None = None
    confidence: float = 1.0
    ocr_metadata: Dict[str, Any] | None = None


class ContextQueryResponse(BaseModel):
    items: List[ContextRecord]


class GoalSuggestionRequest(BaseModel):
    history: List[Dict[str, Any]] = Field(default_factory=list)
    current_actions: List[Dict[str, Any]] = Field(default_factory=list)
    goal_state: Dict[str, Any] | None = None


class GoalSuggestionResponse(BaseModel):
    suggestions: List[Dict[str, Any]]


class TokenUsageResponse(BaseModel):
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
        items = [ContextRecord.model_validate(record) for record in raw_records]
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
