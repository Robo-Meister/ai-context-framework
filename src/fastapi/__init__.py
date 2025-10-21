"""Lightweight FastAPI compatibility layer for tests.

This module provides a minimal subset of the FastAPI API surface that is
required by the unit tests in this kata.  It is *not* a full featured web
framework implementation – it only implements the functionality that the test
suite exercises.  The real project depends on the external ``fastapi``
package, but that dependency is intentionally unavailable in the execution
environment.  Implementing this shim keeps the public API stable while making
it possible to run the tests without installing FastAPI.

The implementation focuses on request/response registration and dispatching
for synchronous usage.  ``TestClient`` drives handlers directly, turning
request payloads into lightweight model objects and coercing query parameters
to the annotated types.  Middleware hooks, background tasks and many other
features are intentionally omitted to keep the surface area tiny.
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import typing
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Mapping, MutableMapping, Sequence, get_args, get_origin, get_type_hints

__all__ = [
    "FastAPI",
    "HTTPException",
    "JSONResponse",
    "Query",
    "Request",
    "Response",
    "TestClient",
    "status",
]


class HTTPException(Exception):
    """Exception used to signal HTTP errors from route handlers."""

    def __init__(self, *, status_code: int, detail: Any | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class status:
    """Subset of HTTP status codes referenced by the code base."""

    HTTP_200_OK = 200
    HTTP_204_NO_CONTENT = 204
    HTTP_401_UNAUTHORIZED = 401
    HTTP_404_NOT_FOUND = 404
    HTTP_429_TOO_MANY_REQUESTS = 429
    HTTP_422_UNPROCESSABLE_ENTITY = 422
    HTTP_500_INTERNAL_SERVER_ERROR = 500


class Query:
    """Marker used to provide metadata and defaults for query parameters."""

    def __init__(self, default: Any = None, *, description: str | None = None) -> None:
        self.default = default
        self.description = description


@dataclass
class RequestClient:
    host: str = "testclient"


class Request:
    """Extremely small representation of a request used by middleware hooks."""

    def __init__(
        self,
        *,
        query_params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
        client: RequestClient | None = None,
        path: str = "/",
        method: str = "GET",
    ) -> None:
        self.query_params = dict(query_params or {})
        self.headers = dict(headers or {})
        self.client = client or RequestClient()
        self.url = type("URL", (), {"path": path})()
        self.method = method


def _serialise(content: Any) -> Any:
    if is_dataclass(content):
        return asdict(content)
    if isinstance(content, Mapping):
        return {key: _serialise(value) for key, value in content.items()}
    if isinstance(content, Sequence) and not isinstance(content, (str, bytes, bytearray)):
        return [_serialise(item) for item in content]
    return content


class Response:
    """Simple response container used by the compatibility layer."""

    def __init__(self, content: Any = None, status_code: int = status.HTTP_200_OK) -> None:
        self.content = content
        self.status_code = status_code

    def json(self) -> Any:
        return _serialise(self.content)


class JSONResponse(Response):
    """Specialised response that always serialises to JSON payloads."""

    def __init__(self, content: Any, status_code: int = status.HTTP_200_OK) -> None:
        super().__init__(content=content, status_code=status_code)


@dataclass
class _Route:
    method: str
    path: str
    handler: Callable[..., Any]


class FastAPI:
    """Very small subset of the FastAPI application interface."""

    def __init__(self, *, title: str = "FastAPI", version: str = "0.1.0") -> None:
        self.title = title
        self.version = version
        self._routes: Dict[tuple[str, str], _Route] = {}
        self._middleware: list[Any] = []

    # ------------------------------------------------------------------
    # Route registration helpers
    def _register_route(
        self,
        method: str,
        path: str,
        handler: Callable[..., Any],
    ) -> Callable[..., Any]:
        self._routes[(path, method)] = _Route(method, path, handler)
        return handler

    def get(self, path: str, *, response_model: Any | None = None):  # noqa: D401 - match FastAPI signature
        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            return self._register_route("GET", path, handler)

        return decorator

    def post(self, path: str, *, response_model: Any | None = None):  # noqa: D401 - match FastAPI signature
        def decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            return self._register_route("POST", path, handler)

        return decorator

    # ------------------------------------------------------------------
    # Middleware handling – the shim only records middleware definitions so
    # tests can introspect the configuration if needed.  The middleware stack
    # is not executed because the tests in this kata never rely on it.
    def add_middleware(self, middleware: Any, **kwargs: Any) -> None:
        instance = middleware(self, **kwargs)
        self._middleware.append(instance)

    # ------------------------------------------------------------------
    # Utilities for the TestClient
    def get_route(self, path: str, method: str) -> _Route:
        try:
            return self._routes[(path, method)]
        except KeyError as exc:  # pragma: no cover - guard for programming errors
            raise ValueError(f"No route registered for {method} {path}") from exc


# ----------------------------------------------------------------------
# Helper utilities used by the TestClient implementation

def _is_dataclass_type(annotation: Any) -> bool:
    return isinstance(annotation, type) and dataclasses.is_dataclass(annotation)


def _construct_body_argument(annotation: Any, payload: Any) -> Any:
    try:
        if _is_dataclass_type(annotation):
            if hasattr(annotation, "from_dict"):
                return annotation.from_dict(payload)
            return annotation(**payload)
        if hasattr(annotation, "from_dict"):
            return annotation.from_dict(payload)
        if hasattr(annotation, "model_validate"):
            return annotation.model_validate(payload)  # pragma: no cover - compatibility path
        return payload
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


def _extract_default(parameter: inspect.Parameter) -> Any:
    if isinstance(parameter.default, Query):
        return parameter.default.default
    if parameter.default is inspect._empty:
        return None
    return parameter.default


def _normalise_target(annotation: Any) -> Any:
    if annotation is inspect.Signature.empty or annotation is None:
        return annotation
    origin = get_origin(annotation)
    if origin is None:
        return annotation
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if args:
        return args[0]
    return annotation


def _coerce_parameter(annotation: Any, value: Any) -> Any:
    if value is None:
        return value
    target = _normalise_target(annotation)
    if target in {int, float, str, bool}:
        return target(value)
    if target is datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)
    return value


def _get_resolved_annotation(type_hints: Dict[str, Any], parameter: inspect.Parameter, name: str) -> Any:
    return type_hints.get(name, parameter.annotation)


def _build_body_arguments(handler: Callable[..., Any], payload: Any) -> Dict[str, Any]:
    signature = inspect.signature(handler)
    type_hints = _safe_get_type_hints(handler)
    arguments: Dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        annotation = _get_resolved_annotation(type_hints, parameter, name)
        arguments[name] = _construct_body_argument(annotation, payload)
    return arguments


def _build_query_arguments(handler: Callable[..., Any], params: Mapping[str, Any]) -> Dict[str, Any]:
    signature = inspect.signature(handler)
    type_hints = _safe_get_type_hints(handler)
    arguments: Dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        default = _extract_default(parameter)
        value = params.get(name, default)
        annotation = _get_resolved_annotation(type_hints, parameter, name)
        arguments[name] = _coerce_parameter(annotation, value)
    return arguments


def _safe_get_type_hints(handler: Callable[..., Any]) -> Dict[str, Any]:
    try:
        return get_type_hints(handler)
    except Exception:  # pragma: no cover - fall back to unresolved annotations
        return {}


async def _maybe_await(result: Any) -> Any:
    if inspect.isawaitable(result):
        return await result
    return result


def _normalise_response(result: Any) -> Response:
    if isinstance(result, Response):
        return result
    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    if is_dataclass(result):
        return Response(content=result, status_code=status.HTTP_200_OK)
    if isinstance(result, Mapping):
        return JSONResponse(dict(result))
    if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
        return JSONResponse(list(result))
    return Response(content=result, status_code=status.HTTP_200_OK)


def _run_handler(handler: Callable[..., Any], **kwargs: Any) -> Response | typing.Coroutine[Any, Any, Response]:
    try:
        result = handler(**kwargs)
    except HTTPException as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    if inspect.isawaitable(result):
        async def _await_and_normalise() -> Response:
            resolved = await _maybe_await(result)
            return _normalise_response(resolved)

        return _await_and_normalise()

    return _normalise_response(result)


# ----------------------------------------------------------------------
# Public TestClient API – exposed as fastapi.testclient.TestClient


class TestClient:
    """Synchronous test client that exercises handlers directly."""

    __test__ = False  # Prevent pytest from attempting to collect this helper as a test case.

    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def __enter__(self) -> "TestClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def _build_request(self, *, path: str, method: str, params: Mapping[str, Any] | None = None) -> Request:
        return Request(query_params=params or {}, path=path, method=method)

    def _execute_with_middlewares(
        self,
        request: Request,
        final_handler: Callable[[], Response | typing.Coroutine[Any, Any, Response]],
    ) -> Response:
        if not self.app._middleware:
            result = final_handler()
            if inspect.isawaitable(result):
                return asyncio.run(result)
            return result

        async def call_chain(index: int, req: Request) -> Response:
            if index >= len(self.app._middleware):
                result_inner = final_handler()
                if inspect.isawaitable(result_inner):
                    return await result_inner
                return result_inner

            middleware = self.app._middleware[index]

            async def next_call(next_req: Request) -> Response:
                return await call_chain(index + 1, next_req)

            return await middleware.dispatch(req, next_call)

        result = asyncio.run(call_chain(0, request))
        if isinstance(result, Response):
            return result
        return _normalise_response(result)

    def post(self, path: str, *, json: MutableMapping[str, Any] | None = None) -> Response:
        route = self.app.get_route(path, "POST")
        payload = json or {}
        try:
            kwargs = _build_body_arguments(route.handler, payload)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

        def final_handler() -> Response:
            return _run_handler(route.handler, **kwargs)

        request = self._build_request(path=path, method="POST")
        return self._execute_with_middlewares(request, final_handler)

    def get(self, path: str, *, params: MutableMapping[str, Any] | None = None) -> Response:
        route = self.app.get_route(path, "GET")
        query_params = params or {}
        kwargs = _build_query_arguments(route.handler, query_params)

        def final_handler() -> Response:
            return _run_handler(route.handler, **kwargs)

        request = self._build_request(path=path, method="GET", params=query_params)
        return self._execute_with_middlewares(request, final_handler)


# Convenience modules mimicking the structure of the external FastAPI package
from . import responses as responses  # noqa: E402,F401
from . import testclient as testclient  # noqa: E402,F401
