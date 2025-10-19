"""Tests for the lightweight YAML compatibility layer."""

from __future__ import annotations

import io

import yaml


def test_safe_load_parses_simple_mapping():
    doc = """
    name: Robo
    age: 5
    """
    result = yaml.safe_load(doc)
    assert result == {"name": "Robo", "age": 5}


def test_safe_load_supports_lists_and_nested_dicts():
    doc = """
    items:
      - type: sensor
        enabled: true
      - type: actuator
        params:
          speed: 3.5
    """
    result = yaml.safe_load(doc)
    assert result == {
        "items": [
            {"type": "sensor", "enabled": True},
            {"type": "actuator", "params": {"speed": 3.5}},
        ]
    }


def test_safe_dump_roundtrip():
    payload = {"alpha": 1, "beta": ["x", "y"]}
    buffer = io.StringIO()
    yaml.safe_dump(payload, buffer)
    buffer.seek(0)
    assert yaml.safe_load(buffer) == payload


def test_safe_load_handles_comments_and_markers():
    doc = """
    # initial comment
    ---
    flag: true  # inline comment
    ...
    """
    assert yaml.safe_load(doc) == {"flag": True}


def test_safe_load_parses_scalar_values():
    assert yaml.safe_load("null") is None
    assert yaml.safe_load("42") == 42
    assert yaml.safe_load("3.14") == 3.14


def test_safe_load_inline_structures():
    assert yaml.safe_load("[1, 2, 3]") == [1, 2, 3]
    assert yaml.safe_load("{foo: bar, answer: 42}") == {"foo": "bar", "answer": 42}
