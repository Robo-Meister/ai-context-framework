"""Minimal base classes mimicking Starlette middleware interfaces."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from fastapi import Request, Response

CallNext = Callable[[Request], Awaitable[Response]]


class BaseHTTPMiddleware:
    """Base middleware compatible with the lightweight FastAPI shim."""

    def __init__(self, app: Any, **_: Any) -> None:
        self.app = app

    async def dispatch(self, request: Request, call_next: CallNext) -> Response:  # pragma: no cover - interface method
        return await call_next(request)


__all__ = ["BaseHTTPMiddleware"]
