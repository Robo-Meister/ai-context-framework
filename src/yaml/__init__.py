"""Small subset of the :mod:`yaml` API used in the tests."""

from __future__ import annotations

import json
from typing import Any

__all__ = ["safe_dump", "safe_load"]


def safe_dump(data: Any, stream=None, **kwargs):  # pragma: no cover - thin wrapper
    text = json.dumps(data, indent=2, sort_keys=True)
    if stream is None:
        return text
    stream.write(text)
    return text


def safe_load(stream):
    if hasattr(stream, "read"):
        content = stream.read()
    else:
        content = stream
    if not content:
        return None
    return json.loads(content)

