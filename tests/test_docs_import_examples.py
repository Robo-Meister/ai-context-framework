"""Smoke-test import paths used in documentation examples."""

import importlib

import pytest


DOC_EXAMPLE_MODULES = [
    "caiengine.core.context_manager",
    "caiengine.core.distributed_context_manager",
    "caiengine.network.network_manager",
    "caiengine.network.simple_network",
    "caiengine.core.fuser",
]

OPTIONAL_DOC_EXAMPLE_MODULES = [
    "caiengine.providers.redis_context_provider",
]


def test_documented_modules_are_importable() -> None:
    for module_path in DOC_EXAMPLE_MODULES:
        module = importlib.import_module(module_path)
        assert module is not None, f"Failed to import documented module: {module_path}"


def test_optional_documented_modules_are_importable_when_dependencies_exist() -> None:
    pytest.importorskip("pydantic")
    for module_path in OPTIONAL_DOC_EXAMPLE_MODULES:
        module = importlib.import_module(module_path)
        assert module is not None, f"Failed to import documented module: {module_path}"
