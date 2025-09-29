from typing import Any, Dict, List, Optional


class ModelRegistry:
    """Simple registry for storing and retrieving models.

    The registry itself is backend agnostic and relies on a provided backend
    object to persist entries.  The backend is expected to implement three
    methods: ``register``, ``list`` and ``fetch``.
    """

    def __init__(self, backend: Any):
        self.backend = backend

    def register(self, model_id: str, version: str, data: Dict[str, Any]) -> None:
        """Register a model entry with the underlying backend."""
        self.backend.register(model_id, version, data)

    def list(self) -> List[Dict[str, Any]]:
        """Return all registered models from the backend."""
        return self.backend.list()

    def fetch(self, model_id: str, version: str) -> Optional[Dict[str, Any]]:
        """Retrieve a model by identifier and version."""
        return self.backend.fetch(model_id, version)
