"""Response utilities for the FastAPI compatibility layer."""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import Response


class JSONResponse(Response):
    """JSON response mirroring FastAPI's behaviour for the exercised tests."""

    def __init__(self, content: Any, status_code: int = 200, headers: Optional[Dict[str, Any]] = None):
        super().__init__(content=content, status_code=status_code, headers=headers)


__all__ = ["JSONResponse"]
