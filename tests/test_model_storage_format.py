import importlib.util
import json
import pathlib
import sys
import types
from dataclasses import asdict

import pytest

torch = pytest.importorskip("torch")
if not hasattr(torch, "device"):
    pytest.skip(
        "PyTorch optional dependencies are not available.",
        allow_module_level=True,
    )
nn = pytest.importorskip("torch.nn")

# Set up lightweight package structure to avoid importing heavy dependencies
SRC_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "caiengine"

caiengine_pkg = types.ModuleType("caiengine")
caiengine_pkg.__path__ = []
sys.modules.setdefault("caiengine", caiengine_pkg)

objects_pkg = types.ModuleType("caiengine.objects")
objects_pkg.__path__ = []
sys.modules.setdefault("caiengine.objects", objects_pkg)

spec_meta = importlib.util.spec_from_file_location(
    "caiengine.objects.model_metadata", SRC_ROOT / "objects" / "model_metadata.py"
)
model_metadata_module = importlib.util.module_from_spec(spec_meta)
spec_meta.loader.exec_module(model_metadata_module)
sys.modules["caiengine.objects.model_metadata"] = model_metadata_module
ModelMetadata = model_metadata_module.ModelMetadata

core_pkg = types.ModuleType("caiengine.core")
core_pkg.__path__ = []
sys.modules.setdefault("caiengine.core", core_pkg)

spec_storage = importlib.util.spec_from_file_location(
    "caiengine.core.model_storage", SRC_ROOT / "core" / "model_storage.py"
)
model_storage_module = importlib.util.module_from_spec(spec_storage)
spec_storage.loader.exec_module(model_storage_module)
save_model_with_metadata = model_storage_module.save_model_with_metadata
load_model_with_metadata = model_storage_module.load_model_with_metadata


class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(2, 1)

    def forward(self, x):  # pragma: no cover - not used in tests
        return self.linear(x)


def create_sample_model_and_metadata():
    model = SimpleModel()
    with torch.no_grad():
        model.linear.weight.fill_(1.0)
        model.linear.bias.fill_(0.5)

    metadata = ModelMetadata(
        model_name="simple",
        version="1.0",
        supported_context_types=["text", "image"],
        training_hash="abc123",
    )
    return model, metadata


def test_round_trip_save_load(tmp_path):
    model, metadata = create_sample_model_and_metadata()
    save_model_with_metadata(model, metadata, tmp_path)

    loaded_model, loaded_meta = load_model_with_metadata(SimpleModel, tmp_path)

    assert asdict(loaded_meta) == asdict(metadata)
    for p_orig, p_loaded in zip(model.parameters(), loaded_model.parameters()):
        assert torch.equal(p_orig, p_loaded)


def test_metadata_integrity(tmp_path):
    model, metadata = create_sample_model_and_metadata()
    save_model_with_metadata(model, metadata, tmp_path)
    with open(tmp_path / "metadata.json", "r", encoding="utf-8") as fh:
        on_disk = json.load(fh)
    assert on_disk == asdict(metadata)
