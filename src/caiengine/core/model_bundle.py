"""Utilities for exporting models to portable ONNX bundles."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import yaml

from caiengine.objects.model_manifest import ModelManifest

MODEL_ONNX_FILENAME = "model.onnx"
MANIFEST_FILENAME = "manifest.yaml"


def export_onnx_bundle(
    model: nn.Module,
    example_input: Any,
    manifest: ModelManifest,
    directory: str | Path,
) -> None:
    """Export ``model`` and its ``manifest`` into ``directory``.

    The model is exported to ONNX format using the provided ``example_input`` to
    trace the model graph. ``manifest`` is serialized to YAML.
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(model, example_input, dir_path / MODEL_ONNX_FILENAME)
    with open(dir_path / MANIFEST_FILENAME, "w", encoding="utf-8") as fh:
        yaml.safe_dump(asdict(manifest), fh)


def load_model_manifest(directory: str | Path) -> ModelManifest:
    """Load a :class:`ModelManifest` from ``directory``."""
    dir_path = Path(directory)
    with open(dir_path / MANIFEST_FILENAME, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return ModelManifest(**data)
