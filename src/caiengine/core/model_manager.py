import json
import os
import shutil
import zipfile
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlretrieve


def _is_remote(path: str) -> bool:
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https")


def _transport_path(src: str, dest: str) -> str:
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    if _is_remote(src):
        urlretrieve(src, dest)
    else:
        shutil.copy(src, dest)
    return dest


def transport_model(src: str, dest: str) -> str:
    """Legacy JSON-model transport helper.

    This function is kept for backward compatibility with existing JSON model
    workflows. Prefer :func:`transport_bundle` for zipped ONNX bundles.
    """
    return _transport_path(src, dest)


def transport_bundle(src: str, dest: str) -> str:
    """Copy or download a model bundle archive between storage backends.

    If ``src`` is a remote URL (http/https), it is downloaded to ``dest``.
    Otherwise the local file is copied.
    """
    return _transport_path(src, dest)


def check_version(path: str, expected: str) -> bool:
    """Legacy JSON version check.

    This function reads a JSON model file and compares its ``version`` field.
    It is kept for backward compatibility. Prefer :func:`check_bundle_version`
    for zipped model bundles.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("version") == expected


def check_bundle_version(bundle_path: str, expected_version: str) -> bool:
    """Return True if ``manifest.yaml`` version in ``bundle_path`` matches expected."""
    with zipfile.ZipFile(bundle_path, "r") as archive:
        manifest_bytes = archive.read("manifest.yaml")
    manifest = _load_manifest_mapping(manifest_bytes)
    return manifest.get("version") == expected_version


def upgrade_schema(path: str, target_version: str) -> None:
    """Upgrade the model schema by setting its version fields.

    The function reads the JSON model file at ``path`` and updates the
    ``version`` and ``schema_version`` fields to ``target_version``.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["version"] = target_version
    data["schema_version"] = target_version
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _load_manifest_mapping(raw: bytes) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError:
        yaml = None

    text = raw.decode("utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError("manifest.yaml must deserialize to a mapping")
        return data

    parsed: dict[str, Any] = {}
    for line in text.splitlines():
        item = line.strip()
        if not item or item.startswith("#") or ":" not in item:
            continue
        key, value = item.split(":", 1)
        value = value.strip()
        if not value:
            parsed[key.strip()] = None
            continue
        try:
            parsed[key.strip()] = json.loads(value)
        except json.JSONDecodeError:
            parsed[key.strip()] = value.strip("\"'")
    return parsed
