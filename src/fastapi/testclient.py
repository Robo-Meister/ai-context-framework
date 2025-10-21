"""Compatibility shim for ``fastapi.testclient``."""
from __future__ import annotations

from . import TestClient

__all__ = ["TestClient"]
