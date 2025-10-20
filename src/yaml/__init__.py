"""Small subset of the :mod:`yaml` API used in the tests."""

from __future__ import annotations

import json
from typing import Any

__all__ = ["safe_dump", "safe_load"]

_CAIENGINE_STUB = True


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
    if content is None:
        return None
    if isinstance(content, bytes):  # pragma: no cover - defensive
        content = content.decode("utf-8")
    content = str(content)
    if not content.strip():
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return _parse_simple_yaml(content)


def _parse_simple_yaml(text: str):
    lines = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw[indent:]
        if stripped.startswith("#") or stripped in {"---", "..."}:
            continue
        stripped = _remove_inline_comment(stripped)
        if not stripped:
            continue
        lines.append((indent, stripped))

    if not lines:
        return None

    value, index = _parse_block(lines, 0, lines[0][0])
    return value


def _parse_block(lines, index, current_indent):
    if index >= len(lines):
        return None, index

    indent, text = lines[index]
    if indent < current_indent:
        return None, index
    if indent > current_indent:
        raise ValueError("Invalid indentation in YAML content")

    if text.startswith("- "):
        return _parse_list(lines, index, current_indent)

    if text.startswith("{") or text.startswith("["):
        return _parse_scalar(text), index + 1

    if ":" not in text:
        return _parse_scalar(text), index + 1

    return _parse_mapping(lines, index, current_indent)


def _remove_inline_comment(text: str) -> str:
    in_single = False
    in_double = False
    for idx, char in enumerate(text):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return text[:idx].rstrip()
    return text.rstrip()


def _parse_list(lines, index, current_indent):
    items = []
    while index < len(lines):
        indent, text = lines[index]
        if indent != current_indent or not text.startswith("- "):
            break

        remainder = text[2:].strip()
        index += 1

        if remainder:
            if ":" in remainder:
                key, value_part = remainder.split(":", 1)
                key = key.strip()
                value_part = value_part.strip()
                if value_part:
                    scalar = _parse_scalar(value_part)
                else:
                    scalar = None
                child = None
                if index < len(lines) and lines[index][0] > current_indent:
                    child_indent = lines[index][0]
                    child, index = _parse_block(lines, index, child_indent)
                item = {key: scalar}
                if child is not None:
                    if scalar is None:
                        item[key] = child
                    elif isinstance(child, dict):
                        item.update(child)
                    else:
                        item[key] = child
                items.append(item)
                continue

            value = _parse_scalar(remainder)
            if index < len(lines) and lines[index][0] > current_indent:
                child_indent = lines[index][0]
                child, index = _parse_block(lines, index, child_indent)
                if child is not None:
                    value = child
            items.append(value)
            continue

        if index >= len(lines) or lines[index][0] <= current_indent:
            items.append(None)
            continue
        child_indent = lines[index][0]
        child, index = _parse_block(lines, index, child_indent)
        items.append(child)

    return items, index


def _parse_mapping(lines, index, current_indent):
    mapping = {}
    while index < len(lines):
        indent, text = lines[index]
        if indent != current_indent or text.startswith("- "):
            break

        if ":" not in text:
            raise ValueError("Invalid mapping entry in YAML content")

        key, remainder = text.split(":", 1)
        key = key.strip()
        remainder = remainder.strip()
        index += 1

        if remainder:
            value = _parse_scalar(remainder)
        else:
            if index < len(lines) and lines[index][0] > current_indent:
                child_indent = lines[index][0]
                value, index = _parse_block(lines, index, child_indent)
            else:
                value = None

        mapping[key] = value

    return mapping, index


def _parse_scalar(text):
    lowered = text.lower()
    if lowered in {"null", "none", "~"}:
        return None
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False

    if (text.startswith("\"") and text.endswith("\"")) or (
        text.startswith("'") and text.endswith("'")
    ):
        return text[1:-1]

    try:
        if any(ch in text for ch in [".", "e", "E"]):
            return float(text)
        return int(text)
    except ValueError:
        pass

    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return [_parse_scalar(part.strip()) for part in inner.split(",")]

    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        if not inner:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            result = {}
            for part in inner.split(","):
                if ":" not in part:
                    raise ValueError("Invalid inline mapping")
                key, value_part = part.split(":", 1)
                result[key.strip()] = _parse_scalar(value_part.strip())
            return result

    return text

