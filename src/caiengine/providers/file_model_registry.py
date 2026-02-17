import fnmatch
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class FileModelRegistry:
    """File based backend for :class:`ModelRegistry`.

    Each registered model is stored as a JSON file on disk using the naming
    convention ``<model_id>-<version>.json``.
    """

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        os.makedirs(self.folder_path, exist_ok=True)

    def _file_path(self, model_id: str, version: str) -> str:
        safe_id = model_id.replace(os.sep, "_")
        safe_version = version.replace(os.sep, "_")
        filename = f"{safe_id}-{safe_version}.json"
        return os.path.join(self.folder_path, filename)

    def _read_record(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _normalize_record(self, model_id: str, version: str, data: Dict[str, Any]) -> Dict[str, Any]:
        manifest = data.get("manifest") if isinstance(data.get("manifest"), dict) else data
        tags = manifest.get("tags") if isinstance(manifest.get("tags"), list) else []
        created_at = manifest.get("created_at")
        if not created_at:
            created_at = datetime.now(timezone.utc).isoformat()

        return {
            "id": model_id,
            "version": version,
            "task": manifest.get("task"),
            "tags": tags,
            "artifact_path": data.get("artifact_path") or manifest.get("artifact_path"),
            "manifest": manifest,
            "created_at": created_at,
            "data": data,
        }

    def register(self, model_id: str, version: str, data: Dict[str, Any]) -> None:
        """Persist model information to disk."""
        path = self._file_path(model_id, version)
        record = self._normalize_record(model_id, version, data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f)

    def list(self) -> List[Dict[str, Any]]:
        """Return all models stored on disk."""
        results: List[Dict[str, Any]] = []
        for fname in os.listdir(self.folder_path):
            if fname.endswith(".json"):
                path = os.path.join(self.folder_path, fname)
                results.append(self._read_record(path))
        return results

    def _value_matches(self, actual: Any, expected: Any) -> bool:
        if isinstance(expected, str) and "*" in expected:
            return isinstance(actual, str) and fnmatch.fnmatch(actual, expected)
        return actual == expected

    def _matches(self, record: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        manifest = record.get("manifest") if isinstance(record.get("manifest"), dict) else {}

        for key, expected in criteria.items():
            if key == "tags":
                actual_tags = record.get("tags") or []
                expected_tags = expected if isinstance(expected, list) else [expected]
                if not all(tag in actual_tags for tag in expected_tags):
                    return False
                continue

            actual = record.get(key)
            if actual is None and key in manifest:
                actual = manifest.get(key)
            if not self._value_matches(actual, expected):
                return False

        return True

    def find(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find records matching exact and wildcard criteria."""
        return [record for record in self.list() if self._matches(record, criteria)]

    def fetch(self, model_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific model entry."""
        path = self._file_path(model_id, version)
        if not os.path.exists(path):
            return None
        return self._read_record(path)
