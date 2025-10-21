"""Lightweight FastAPI compatibility layer for testing.

This module provides a very small subset of FastAPI's public interface that is
required by the unit tests in this kata.  It intentionally avoids network
stack dependencies and focuses solely on request handling and dependency
injection for synchronous testing.  The goal is to keep the real package
optional while maintaining comparable behaviour for the exercised endpoints.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional


class HTTPException(Exception):
    """Exception used to signal HTTP error responses."""

    def __init__(self, status_code: int, detail: Any = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _StatusCodes:
    HTTP_401_UNAUTHORIZED = 401
    HTTP_429_TOO_MANY_REQUESTS = 429
    HTTP_500_INTERNAL_SERVER_ERROR = 500
    HTTP_404_NOT_FOUND = 404
    HTTP_422_UNPROCESSABLE_ENTITY = 422


status = _StatusCodes()


class QueryParam:
    """Descriptor capturing metadata for query parameters."""

    __slots__ = ("default", "description")

    def __init__(self, default: Any = None, description: str | None = None):
        self.default = default
        self.description = description


def Query(*, default: Any = None, description: str | None = None) -> QueryParam:
    """Return a lightweight representation of a FastAPI query parameter."""

    return QueryParam(default=default, description=description)


class Request:
    """Simplified request object passed through middleware and endpoints."""

    def __init__(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        query_params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        client_host: str = "testclient",
    ) -> None:
        self.method = method.upper()
        self._json = json
        self.query_params = query_params or {}
        self.headers = headers or {}
        self.client = SimpleNamespace(host=client_host)
        self.url = SimpleNamespace(path=path)
        self.app: "FastAPI" | None = None

    def json(self) -> Any:
        return self._json


class Response:
    """Basic HTTP response container used by the compatibility layer."""

    def __init__(self, content: Any = None, status_code: int = 200, headers: Optional[Dict[str, Any]] = None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> Any:
        return self.content


@dataclass
class _Route:
    method: str
    path: str
    func: Callable[..., Any]
    response_model: Any | None


class FastAPI:
    """Minimal application object supporting routing and middleware."""

    def __init__(self, *, title: str | None = None, version: str | None = None) -> None:
        self.title = title
        self.version = version
        self._routes: List[_Route] = []
        self._middleware: List[Any] = []

    # ------------------------------------------------------------------ routing
    def route(self, path: str, *, methods: List[str], response_model: Any | None = None):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._routes.append(
                _Route(method=methods[0].upper(), path=path, func=func, response_model=response_model)
            )
            return func

        return decorator

    def get(self, path: str, *, response_model: Any | None = None):
        return self.route(path, methods=["GET"], response_model=response_model)

    def post(self, path: str, *, response_model: Any | None = None):
        return self.route(path, methods=["POST"], response_model=response_model)

    # ---------------------------------------------------------------- middleware
    def add_middleware(self, middleware_class: type, **options: Any) -> None:
        instance = middleware_class(self, **options)
        self._middleware.append(instance)

    # ----------------------------------------------------------------- utilities
    def _find_route(self, method: str, path: str) -> _Route | None:
        for route in self._routes:
            if route.method == method and route.path == path:
                return route
        return None

    async def _handle_request(self, request: Request) -> Response:
        request.app = self
        route = self._find_route(request.method, request.url.path)
        if route is None:
            return Response({"detail": "Not Found"}, status_code=status.HTTP_404_NOT_FOUND)

        async def endpoint(req: Request) -> Response:
            return await self._execute_route(route, req)

        async def call_with_middleware(index: int, req: Request) -> Response:
            if index >= len(self._middleware):
                return await endpoint(req)
            middleware = self._middleware[index]

            async def call_next(inner_req: Request) -> Response:
                return await call_with_middleware(index + 1, inner_req)

            return await middleware.dispatch(req, call_next)

        try:
            return await call_with_middleware(0, request)
        except HTTPException as exc:  # convert to JSON payload
            content = {"detail": exc.detail}
            return Response(content, status_code=exc.status_code)

    async def _execute_route(self, route: _Route, request: Request) -> Response:
        kwargs = self._build_parameters(route.func, request)
        result = route.func(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return self._build_response(result)

    # ---------------------------------------------------------------- conversion
    def _build_parameters(self, func: Callable[..., Any], request: Request) -> Dict[str, Any]:
        signature = inspect.signature(func)
        body_payload = request.json()
        params: Dict[str, Any] = {}
        for name, param in signature.parameters.items():
            annotation = param.annotation

            if annotation is Request or name == "request":
                params[name] = request
                continue

            default = param.default
            if isinstance(default, QueryParam):
                params[name] = request.query_params.get(name, default.default)
                continue

            if request.method in {"POST", "PUT", "PATCH"} and body_payload is not None:
                params[name] = body_payload
            elif default is not inspect._empty:
                params[name] = default
            else:
                params[name] = None
        return params

    def _build_response(self, result: Any) -> Response:
        if isinstance(result, Response):
            return result
        if isinstance(result, dict):
            return Response(result, status_code=200)
        if result is None:
            return Response(None, status_code=200)
        return Response(result, status_code=200)


__all__ = [
    "FastAPI",
    "HTTPException",
    "Query",
    "QueryParam",
    "Request",
    "Response",
    "status",
]
