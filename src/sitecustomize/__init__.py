"""Runtime shims for optional third-party integrations."""

from __future__ import annotations

from functools import wraps
from textwrap import dedent
from typing import Any


def _normalise_yaml_input(stream: Any) -> tuple[Any, bool]:
    if stream is None:
        return stream, False
    if hasattr(stream, "read"):
        content = stream.read()
        if isinstance(content, (bytes, bytearray)):
            content = content.decode("utf-8")
        return content, True
    if isinstance(stream, (bytes, bytearray)):
        return stream.decode("utf-8"), True
    if isinstance(stream, str):
        return stream, True
    return stream, False


def _patch_yaml_safe_load() -> None:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return

    if getattr(yaml, "_CAIENGINE_STUB", False):
        return

    original = getattr(yaml, "safe_load", None)
    if not callable(original):
        return
    if getattr(original, "__wrapped__", None):
        return

    @wraps(original)
    def safe_load(stream: Any, *args: Any, **kwargs: Any):
        normalised, was_textual = _normalise_yaml_input(stream)
        if was_textual:
            text = dedent(normalised or "")
            return original(text, *args, **kwargs)
        return original(stream, *args, **kwargs)

    safe_load.__wrapped__ = original  # type: ignore[attr-defined]
    yaml.safe_load = safe_load  # type: ignore[assignment]


_patch_yaml_safe_load()
