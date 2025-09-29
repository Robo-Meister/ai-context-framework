import json
import os
import shutil
from urllib.parse import urlparse
from urllib.request import urlretrieve


def _is_remote(path: str) -> bool:
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https")


def transport_model(src: str, dest: str) -> str:
    """Copy or download a model file between storage backends.

    If ``src`` is a remote URL (http/https) it will be downloaded to ``dest``.
    Otherwise the file is copied locally.  The destination directory is
    created if necessary.
    """
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    if _is_remote(src):
        urlretrieve(src, dest)
    else:
        shutil.copy(src, dest)
    return dest


def check_version(path: str, expected: str) -> bool:
    """Return True if the model file at ``path`` matches ``expected`` version."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("version") == expected


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

