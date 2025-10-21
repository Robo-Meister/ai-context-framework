"""Test client for the lightweight FastAPI compatibility layer."""

from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from typing import Any, Dict, Optional

from . import Request


class TestClient(AbstractContextManager["TestClient"]):
    """Small synchronous wrapper used by the unit tests."""

    __test__ = False  # Prevent pytest from treating this as a test case.

    def __init__(self, app) -> None:  # app is the lightweight FastAPI instance
        self.app = app
        self._closed = False

    # ------------------------------------------------------------------ context API
    def __enter__(self) -> "TestClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ public API
    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        if self._closed:
            raise RuntimeError("Client has been closed")
        request = Request(method, path, json=json, query_params=params, headers=headers)
        return asyncio.run(self.app._handle_request(request))

    def post(self, path: str, *, json: Any = None, headers: Optional[Dict[str, Any]] = None):
        return self.request("POST", path, json=json, headers=headers)

    def get(self, path: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, Any]] = None):
        return self.request("GET", path, params=params, headers=headers)

    # --------------------------------------------------------------------- helpers
    def close(self) -> None:
        self._closed = True


__all__ = ["TestClient"]
