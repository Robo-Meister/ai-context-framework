import importlib.util
import pathlib
import sys
import types

import torch
import torch.nn as nn


SRC_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "caiengine"

# Create lightweight package structure
caiengine_pkg = types.ModuleType("caiengine")
caiengine_pkg.__path__ = []
sys.modules.setdefault("caiengine", caiengine_pkg)

objects_pkg = types.ModuleType("caiengine.objects")
objects_pkg.__path__ = []
sys.modules.setdefault("caiengine.objects", objects_pkg)

spec_manifest = importlib.util.spec_from_file_location(
    "caiengine.objects.model_manifest", SRC_ROOT / "objects" / "model_manifest.py"
)
manifest_module = importlib.util.module_from_spec(spec_manifest)
spec_manifest.loader.exec_module(manifest_module)
sys.modules["caiengine.objects.model_manifest"] = manifest_module
ModelManifest = manifest_module.ModelManifest

core_pkg = types.ModuleType("caiengine.core")
core_pkg.__path__ = []
sys.modules.setdefault("caiengine.core", core_pkg)

spec_bundle = importlib.util.spec_from_file_location(
    "caiengine.core.model_bundle", SRC_ROOT / "core" / "model_bundle.py"
)
bundle_module = importlib.util.module_from_spec(spec_bundle)
spec_bundle.loader.exec_module(bundle_module)
export_onnx_bundle = bundle_module.export_onnx_bundle
load_model_manifest = bundle_module.load_model_manifest


class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(2, 1)

    def forward(self, x):  # pragma: no cover - not used
        return self.linear(x)


def test_export_and_load_manifest(tmp_path):
    model = SimpleModel()
    manifest = ModelManifest(model_name="simple", version="1.0")
    dummy_input = torch.randn(1, 2)

    export_onnx_bundle(model, dummy_input, manifest, tmp_path)

    assert (tmp_path / "model.onnx").exists()
    loaded = load_model_manifest(tmp_path)
    assert loaded.model_name == manifest.model_name
    assert loaded.version == manifest.version
