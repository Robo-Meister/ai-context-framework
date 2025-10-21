"""ASGI service exposing context ingestion, retrieval, and goal feedback APIs."""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import logging
import threading
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
from caiengine.core.goal_strategies import SimpleGoalFeedbackStrategy
from caiengine.objects.context_query import ContextQuery
from caiengine.providers.http_context_provider import HTTPContextProvider

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


class CAIService:
    """Combined ASGI service exposing context and goal feedback endpoints."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        backend: object | None = None,
        *,
        auth_hook: AuthHook | None = None,
        error_handler: ErrorHandler | None = None,
        rate_limit_per_minute: int | None = None,
        rate_limit_window_seconds: float = 60.0,
        include_error_details: bool = False,
        rate_limit_identifier: RateLimitIdentifier | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.provider = HTTPContextProvider(host=host, port=port, backend=backend)
        self.feedback_loop = GoalDrivenFeedbackLoop(SimpleGoalFeedbackStrategy())
        self.token_counter = TokenCounter()
        self.auth_hook = auth_hook
        self.error_handler = error_handler
        self.include_error_details = include_error_details
        self.rate_limit = rate_limit_per_minute or 0
        self.rate_limit_window_seconds = rate_limit_window_seconds
        self.rate_limit_identifier = rate_limit_identifier
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.app = self._create_app()
        self._server: Any | None = None
        self._thread: threading.Thread | None = None

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="CAI Engine Service", version="1.0.0")

        if self.error_handler or self.include_error_details:
            app.add_middleware(
                ErrorHandlingMiddleware,
                handler=self.error_handler,
                include_details=self.include_error_details,
            )
        if self.rate_limit > 0:
            app.add_middleware(
                RateLimitMiddleware,
                limit=self.rate_limit,
                window_seconds=self.rate_limit_window_seconds,
                identifier=self.rate_limit_identifier,
            )
        if self.auth_hook:
            app.add_middleware(AuthHookMiddleware, hook=self.auth_hook)

        @app.post("/context", response_model=ContextIngestionResponse)
        async def ingest_context(request: ContextIngestionRequest) -> ContextIngestionResponse:
            try:
                context_id = self.provider.ingest_context(
                    request.payload,
                    timestamp=request.timestamp,
                    metadata=request.metadata,
                    source_id=request.source_id,
                    confidence=request.confidence,
                )
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Context ingestion failed")
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
                raw_records = self.provider.get_context(query)
            except Exception as exc:  # noqa: BLE001
                self.logger.exception("Context retrieval failed")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
            items = [ContextRecord.model_validate(record) for record in raw_records]
            return ContextQueryResponse(items=items)

        @app.post("/suggest", response_model=GoalSuggestionResponse)
        async def suggest_actions(request: GoalSuggestionRequest) -> GoalSuggestionResponse:
            if request.goal_state is not None:
                self.feedback_loop.set_goal_state(request.goal_state)
            suggestions = self.feedback_loop.suggest(request.history, request.current_actions)
            for suggestion in suggestions:
                usage = suggestion.get("usage") if isinstance(suggestion, dict) else None
                if usage:
                    self.token_counter.add(usage)
            return GoalSuggestionResponse(suggestions=suggestions)

        @app.get("/usage", response_model=TokenUsageResponse)
        async def usage() -> TokenUsageResponse:
            usage_payload = self.token_counter.as_dict()
            return TokenUsageResponse(**usage_payload)

        return app

    def _create_server(self):
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_config=None,
        )
        return uvicorn.Server(config)

    def serve(self) -> None:
        """Run the ASGI app using uvicorn in the current thread."""

        server = self._create_server()
        server.run()

    def start(self) -> None:
        """Start the ASGI app in a background thread."""

        if self._thread and self._thread.is_alive():
            return
        self._server = self._create_server()
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.should_exit = True
        if self._thread:
            self._thread.join()
        self._server = None
        self._thread = None


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Start CAIEngine FastAPI service")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    parser.add_argument("--backend", default=None, help="Backend provider class path")
    parser.add_argument(
        "--backend-options",
        default=None,
        help="JSON encoded keyword arguments for the backend provider",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=0,
        help="Maximum number of requests per minute (0 disables limiting)",
    )
    parser.add_argument(
        "--rate-limit-window",
        type=float,
        default=60.0,
        help="Duration of the rate limiting window in seconds",
    )
    parser.add_argument(
        "--include-error-details",
        action="store_true",
        help="Expose exception messages in error responses",
    )
    args = parser.parse_args(argv)

    backend_spec = None
    if args.backend:
        options = json.loads(args.backend_options) if args.backend_options else {}
        backend_spec = {"path": args.backend, "options": options}

    rate_limit = args.rate_limit if args.rate_limit > 0 else None

    service = CAIService(
        host=args.host,
        port=args.port,
        backend=backend_spec,
        rate_limit_per_minute=rate_limit,
        rate_limit_window_seconds=args.rate_limit_window,
        include_error_details=args.include_error_details,
    )
    service.serve()


if __name__ == "__main__":
    main()
