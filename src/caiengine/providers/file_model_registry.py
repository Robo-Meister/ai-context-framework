import json
import os
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

    def register(self, model_id: str, version: str, data: Dict[str, Any]) -> None:
        """Persist model information to disk."""
        path = self._file_path(model_id, version)
        record = {"id": model_id, "version": version, "data": data}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f)

    def list(self) -> List[Dict[str, Any]]:
        """Return all models stored on disk."""
        results: List[Dict[str, Any]] = []
        for fname in os.listdir(self.folder_path):
            if fname.endswith(".json"):
                path = os.path.join(self.folder_path, fname)
                with open(path, "r", encoding="utf-8") as f:
                    results.append(json.load(f))
        return results

    def fetch(self, model_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific model entry."""
        path = self._file_path(model_id, version)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
