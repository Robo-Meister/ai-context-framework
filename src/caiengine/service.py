"""ASGI service exposing context ingestion, retrieval, and goal feedback APIs."""

from __future__ import annotations

import argparse
import json
import logging
import threading
from typing import Any, Iterable

from caiengine.common.token_usage import TokenCounter
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import SimpleGoalFeedbackStrategy
from caiengine.providers.http_context_provider import HTTPContextProvider
from caiengine.providers.http_service import (
    AuthHook,
    ErrorHandler,
    RateLimitIdentifier,
    create_http_service_app,
)


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
        self.app = create_http_service_app(
            provider=self.provider,
            logger=self.logger,
            feedback_loop=self.feedback_loop,
            token_counter=self.token_counter,
            auth_hook=self.auth_hook,
            error_handler=self.error_handler,
            rate_limit_per_minute=self.rate_limit,
            rate_limit_window_seconds=self.rate_limit_window_seconds,
            include_error_details=self.include_error_details,
            rate_limit_identifier=self.rate_limit_identifier,
            include_goal_routes=True,
        )
        self._server: Any | None = None
        self._thread: threading.Thread | None = None

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
