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
from pydantic import BaseModel, ConfigDict, Field, field_validator

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

    async def _check_request(self, request: Request) -> Response | None:
        """Evaluate whether the incoming request should be rate limited."""

        if self.limit <= 0:
            return None

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
        return None

    @staticmethod
    async def _default_identifier(request: Request) -> str:
        if request.client:
            return request.client.host
        return "anonymous"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        blocked = await self._check_request(request)
        if blocked is not None:
            return blocked
        return await call_next(request)

    async def __call__(self, scope, receive, send):  # pragma: no cover - exercised in integration tests
        """ASGI entry-point for compatibility with the real FastAPI stack."""

        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = self._build_request(scope, receive)
        blocked = await self._check_request(request)
        if blocked is not None:
            await self._send_response(scope, receive, send, blocked)
            return

        await self.app(scope, receive, send)

    def _build_request(self, scope, receive) -> Request:
        """Construct a request object for identifier hooks.

        When the external FastAPI dependency is available, ``Request`` will be
        the Starlette request class and can be instantiated directly from the
        ASGI ``scope``.  Otherwise we fall back to the lightweight shim
        implementation which only needs a handful of attributes for the default
        identifier.
        """

        try:  # Prefer the native Starlette request when available.
            return Request(scope, receive=receive)  # type: ignore[arg-type]
        except TypeError:
            from urllib.parse import parse_qs

            query_string = scope.get("query_string", b"")
            params = {
                key: values[0] if isinstance(values, list) and values else values
                for key, values in parse_qs(query_string.decode(), keep_blank_values=True).items()
            }
            headers = {
                key.decode(): value.decode()
                for key, value in scope.get("headers", [])
            }
            client_host = "anonymous"
            client = scope.get("client")
            if client and client[0]:
                client_host = client[0]
            shim_client = type("_ShimClient", (), {"host": client_host})()
            return Request(
                query_params=params,
                headers=headers,
                client=shim_client,
                path=scope.get("path", "/"),
                method=scope.get("method", "GET"),
            )

    async def _send_response(self, scope, receive, send, response: Response) -> None:
        """Send a minimal ASGI response for blocked requests."""

        if hasattr(response, "__call__"):
            await response(scope, receive, send)  # type: ignore[func-returns-value]
            return

        import json

        if isinstance(response, JSONResponse):
            body_content = json.dumps(response.json()).encode("utf-8")
            headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body_content)).encode())]
        else:
            content = response.content if hasattr(response, "content") else None
            body_content = b"" if content is None else str(content).encode("utf-8")
            headers = [(b"content-length", str(len(body_content)).encode())]

        await send({
            "type": "http.response.start",
            "status": getattr(response, "status_code", status.HTTP_200_OK),
            "headers": headers,
        })
        await send({"type": "http.response.body", "body": body_content, "more_body": False})


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid datetime value: {value!r}") from exc


class ContextIngestionRequest(BaseModel):
    payload: Dict[str, Any]
    timestamp: datetime | None = None
    metadata: Dict[str, Any] | None = None
    source_id: str = "http"
    confidence: float = 1.0
    ttl: int | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("payload")
    @classmethod
    def _validate_payload(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("payload must be a mapping")
        return value


class ContextIngestionResponse(BaseModel):
    id: str


class ContextRecord(BaseModel):
    id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = Field(default_factory=dict)
    roles: List[str] = Field(default_factory=list)
    situations: List[str] = Field(default_factory=list)
    content: Any | None = None
    confidence: float = 1.0
    ocr_metadata: Dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")

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


class ContextQueryResponse(BaseModel):
    items: List[ContextRecord]


class GoalSuggestionRequest(BaseModel):
    history: List[Dict[str, Any]] = Field(default_factory=list)
    current_actions: List[Dict[str, Any]] = Field(default_factory=list)
    goal_state: Dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class GoalSuggestionResponse(BaseModel):
    suggestions: List[Dict[str, Any]]


class TokenUsageResponse(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ProviderStatus(BaseModel):
    name: str
    backend: str | None
    ok: bool
    cache_size: int | None = None


class GoalAnalytics(BaseModel):
    history_size: int
    last_suggestions: List[Dict[str, Any]]
    last_analysis: Dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    provider: ProviderStatus


class StatusResponse(HealthResponse):
    goal_analytics: GoalAnalytics | None = None


def _get_cache_size(target: Any) -> int | None:
    cache = getattr(target, "cache", None)
    if cache is None:
        return None
    if hasattr(cache, "cache"):
        cache_mapping = getattr(cache, "cache")
        if isinstance(cache_mapping, dict):
            return len(cache_mapping)
    size_attr = getattr(cache, "size", None)
    if isinstance(size_attr, int):
        return size_attr
    size_fn = getattr(cache, "size", None)
    if callable(size_fn):
        try:
            size = size_fn()
            return int(size)
        except Exception:  # pragma: no cover - defensive
            return None
    return None


def _describe_provider(provider: Any) -> ProviderStatus:
    provider_name = f"{provider.__class__.__module__}.{provider.__class__.__name__}"
    backend = getattr(provider, "backend", None)
    backend_name = None
    cache_size = None
    if backend is not None:
        backend_name = f"{backend.__class__.__module__}.{backend.__class__.__name__}"
        cache_size = _get_cache_size(backend)
    return ProviderStatus(
        name=provider_name,
        backend=backend_name,
        ok=True,
        cache_size=cache_size,
    )


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

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", provider=_describe_provider(provider))

    @app.get("/status", response_model=StatusResponse)
    async def status_endpoint() -> StatusResponse:
        analytics: GoalAnalytics | None = None
        if feedback_loop is not None:
            analytics = GoalAnalytics(
                history_size=len(feedback_loop.history),
                last_suggestions=feedback_loop.last_suggestions,
                last_analysis=feedback_loop.last_analysis,
            )
        return StatusResponse(
            status="ok",
            provider=_describe_provider(provider),
            goal_analytics=analytics,
        )

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
