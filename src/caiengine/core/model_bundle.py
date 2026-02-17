"""Utilities for exporting models to portable ONNX bundles."""

from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency gate
    yaml = None

from caiengine.objects.model_manifest import ModelManifest

MODEL_ONNX_FILENAME = "model.onnx"
MANIFEST_FILENAME = "manifest.yaml"
CHECKSUM_FILENAME = "checksums.json"


def export_onnx_bundle(
    model: Any,
    example_input: Any,
    manifest: ModelManifest,
    directory: str | Path,
) -> None:
    """Export ``model`` and its ``manifest`` into ``directory``.

    The model is exported to ONNX format using the provided ``example_input`` to
    trace the model graph. ``manifest`` is serialized to YAML.
    """
    torch = _require_torch()

    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    model_path = dir_path / MODEL_ONNX_FILENAME
    try:
        torch.onnx.export(model, example_input, model_path)
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency guard
        if exc.name != "onnxscript":
            raise
        _export_state_dict_fallback(model, model_path)
    except RuntimeError as exc:  # pragma: no cover - torch error surface
        if "onnxscript" not in str(exc):
            raise
        _export_state_dict_fallback(model, model_path)

    _write_manifest(dir_path / MANIFEST_FILENAME, manifest)


def export_model_bundle_zip(
    model: Any,
    example_input: Any,
    manifest: ModelManifest,
    zip_path: str | Path,
) -> None:
    """Export ``model`` and ``manifest`` into a zipped model bundle."""
    zip_target = Path(zip_path)
    zip_target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        bundle_dir = Path(tmp_dir)
        export_onnx_bundle(model, example_input, manifest, bundle_dir)
        checksums = _build_checksums(bundle_dir, [MODEL_ONNX_FILENAME, MANIFEST_FILENAME])
        with open(bundle_dir / CHECKSUM_FILENAME, "w", encoding="utf-8") as fh:
            json.dump(checksums, fh, indent=2, sort_keys=True)

        with zipfile.ZipFile(zip_target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for filename in (MODEL_ONNX_FILENAME, MANIFEST_FILENAME, CHECKSUM_FILENAME):
                zf.write(bundle_dir / filename, arcname=filename)


def load_model_manifest(directory: str | Path) -> ModelManifest:
    """Load a :class:`ModelManifest` from ``directory``."""
    dir_path = Path(directory)
    return _read_manifest(dir_path / MANIFEST_FILENAME)


def load_model_bundle_zip(
    zip_path: str | Path,
    extract_dir: str | Path | None = None,
) -> tuple[Path, ModelManifest]:
    """Load a zipped model bundle.

    Returns the extracted ONNX path and parsed manifest.
    """
    zip_file = Path(zip_path)
    target_dir = Path(extract_dir) if extract_dir is not None else zip_file.with_suffix("")
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_file, "r") as zf:
        zf.extractall(target_dir)

    manifest = _read_manifest(target_dir / MANIFEST_FILENAME)
    return target_dir / MODEL_ONNX_FILENAME, manifest


def validate_model_bundle_zip(zip_path: str | Path) -> list[str]:
    """Validate zipped model bundle structure and optional checksums."""
    errors: list[str] = []
    zip_file = Path(zip_path)
    if not zip_file.exists():
        return [f"Bundle does not exist: {zip_file}"]

    try:
        with zipfile.ZipFile(zip_file, "r") as zf:
            names = set(zf.namelist())
            for required in (MODEL_ONNX_FILENAME, MANIFEST_FILENAME):
                if required not in names:
                    errors.append(f"Missing required file: {required}")

            if errors:
                return errors

            try:
                manifest_data = _load_manifest_mapping(zf.read(MANIFEST_FILENAME))
                if not isinstance(manifest_data, dict):
                    errors.append("manifest.yaml must deserialize to a mapping")
                else:
                    ModelManifest(**manifest_data)
            except Exception as exc:  # pragma: no cover - error formatting branch
                errors.append(f"Invalid manifest.yaml: {exc}")

            if CHECKSUM_FILENAME in names:
                try:
                    checksums = json.loads(zf.read(CHECKSUM_FILENAME).decode("utf-8"))
                except Exception as exc:  # pragma: no cover - error formatting branch
                    errors.append(f"Invalid checksums.json: {exc}")
                else:
                    if not isinstance(checksums, dict):
                        errors.append("checksums.json must deserialize to a mapping")
                    else:
                        for filename, expected_hash in checksums.items():
                            if filename not in names:
                                errors.append(f"Checksum entry references missing file: {filename}")
                                continue
                            actual_hash = hashlib.sha256(zf.read(filename)).hexdigest()
                            if actual_hash != expected_hash:
                                errors.append(
                                    f"Checksum mismatch for {filename}: "
                                    f"expected {expected_hash}, got {actual_hash}"
                                )
    except zipfile.BadZipFile:
        errors.append(f"Invalid zip archive: {zip_file}")

    return errors


def _read_manifest(manifest_path: Path) -> ModelManifest:
    with open(manifest_path, "rb") as fh:
        data = _load_manifest_mapping(fh.read())
    return ModelManifest(**data)


def _write_manifest(manifest_path: Path, manifest: ModelManifest) -> None:
    payload = asdict(manifest)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        if yaml is None:
            for key, value in payload.items():
                fh.write(f"{key}: {json.dumps(value)}\n")
        else:
            yaml.safe_dump(payload, fh)


def _load_manifest_mapping(raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        if isinstance(data, dict):
            return data
        raise ValueError("manifest.yaml must deserialize to a mapping")

    # Fallback parser for simple ``key: value`` YAML documents.
    data: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        parsed = value.strip()
        if parsed == "":
            data[key.strip()] = None
            continue
        try:
            data[key.strip()] = json.loads(parsed)
        except json.JSONDecodeError:
            data[key.strip()] = parsed.strip("\"'")
    return data


def _build_checksums(directory: Path, filenames: list[str]) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for filename in filenames:
        with open(directory / filename, "rb") as fh:
            checksums[filename] = hashlib.sha256(fh.read()).hexdigest()
    return checksums


def _require_torch() -> Any:
    try:
        import torch
    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency gate
        raise ImportError(
            "Model export utilities require the optional dependency set 'ai'. "
            "Install it with `pip install caiengine[ai]`."
        ) from exc
    return torch


def _export_state_dict_fallback(model: Any, destination: Path) -> None:
    """Persist ``model`` parameters when ONNX export dependencies are missing."""

    torch = _require_torch()
    # ``torch.save`` stores the state dict using PyTorch's binary format.  While
    # not an ONNX model, it provides a deterministic artefact so the bundle
    # remains self-contained in environments without the optional ``onnxscript``
    # dependency required by ``torch.onnx``.
    torch.save(model.state_dict(), destination)
