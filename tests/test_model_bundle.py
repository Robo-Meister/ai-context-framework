import importlib.util
import pathlib
import sys
import types
import zipfile

import pytest

torch = pytest.importorskip("torch")
if not hasattr(torch, "device"):
    pytest.skip(
        "PyTorch optional dependencies are not available.",
        allow_module_level=True,
    )
nn = pytest.importorskip("torch.nn")
pytest.importorskip("onnx")


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
export_model_bundle_zip = bundle_module.export_model_bundle_zip
load_model_bundle_zip = bundle_module.load_model_bundle_zip
load_model_manifest = bundle_module.load_model_manifest
validate_model_bundle_zip = bundle_module.validate_model_bundle_zip


class SimpleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(2, 1)

    def forward(self, x):  # pragma: no cover - not used
        return self.linear(x)


def _build_manifest() -> ModelManifest:
    return ModelManifest(
        model_name="simple",
        version="1.0",
        engine_version="0.2.1",
        task="regression",
        tags=["tiny", "test"],
        input_schema={"shape": [1, 2], "dtype": "float32"},
        output_schema={"shape": [1, 1], "dtype": "float32"},
        created_at="2026-01-01T00:00:00Z",
    )


def test_export_and_load_manifest(tmp_path):
    model = SimpleModel()
    manifest = _build_manifest()
    dummy_input = torch.randn(1, 2)

    export_onnx_bundle(model, dummy_input, manifest, tmp_path)

    assert (tmp_path / "model.onnx").exists()
    loaded = load_model_manifest(tmp_path)
    assert loaded.model_name == manifest.model_name
    assert loaded.version == manifest.version
    assert loaded.schema_version == manifest.schema_version


def test_export_and_load_model_bundle_zip_round_trip(tmp_path):
    model = SimpleModel()
    manifest = _build_manifest()
    zip_path = tmp_path / "bundle.zip"

    export_model_bundle_zip(model, torch.randn(1, 2), manifest, zip_path)

    with zipfile.ZipFile(zip_path, "r") as archive:
        names = set(archive.namelist())
    assert {"model.onnx", "manifest.yaml", "checksums.json"}.issubset(names)

    extracted_model_path, loaded_manifest = load_model_bundle_zip(
        zip_path, extract_dir=tmp_path / "loaded"
    )
    assert extracted_model_path.exists()
    assert loaded_manifest.model_name == manifest.model_name
    assert loaded_manifest.tags == manifest.tags
    assert loaded_manifest.input_schema == manifest.input_schema

    assert validate_model_bundle_zip(zip_path) == []


def test_validate_model_bundle_zip_catches_missing_required_file(tmp_path):
    zip_path = tmp_path / "invalid.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.yaml", "model_name: bad\nversion: '1.0'\n")

    errors = validate_model_bundle_zip(zip_path)
    assert any("Missing required file: model.onnx" in err for err in errors)
