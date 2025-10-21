"""Compatibility shims for ``fastapi.responses``."""
from __future__ import annotations

from . import JSONResponse, Response

__all__ = ["JSONResponse", "Response"]
