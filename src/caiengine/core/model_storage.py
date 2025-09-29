"""Utilities for persisting models with accompanying metadata."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Tuple, Type

import torch
import torch.nn as nn

from caiengine.objects.model_metadata import ModelMetadata

MODEL_FILENAME = "model.pt"
METADATA_FILENAME = "metadata.json"


def save_model_with_metadata(
    model: nn.Module, metadata: ModelMetadata, directory: str | Path
) -> None:
    """Save ``model`` and ``metadata`` into ``directory``.

    The model's ``state_dict`` is saved using :func:`torch.save` and the metadata
    is serialized to JSON.
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), dir_path / MODEL_FILENAME)
    with open(dir_path / METADATA_FILENAME, "w", encoding="utf-8") as fh:
        json.dump(asdict(metadata), fh)


def load_model_with_metadata(
    model_class: Type[nn.Module], directory: str | Path
) -> Tuple[nn.Module, ModelMetadata]:
    """Load a model and its metadata from ``directory``.

    ``model_class`` should be instantiable without arguments. The returned model
    will have its parameters loaded from the stored state dictionary.
    """
    dir_path = Path(directory)
    with open(dir_path / METADATA_FILENAME, "r", encoding="utf-8") as fh:
        meta_dict = json.load(fh)
    metadata = ModelMetadata(**meta_dict)

    model = model_class()
    state = torch.load(dir_path / MODEL_FILENAME, map_location="cpu")
    model.load_state_dict(state)
    return model, metadata
