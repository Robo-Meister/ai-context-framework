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

    def find(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find models matching the provided criteria.

        The backend may provide a dedicated ``find`` implementation. When it
        does not, this method falls back to in-memory filtering over ``list``.
        """
        backend_find = getattr(self.backend, "find", None)
        if callable(backend_find):
            return backend_find(criteria)

        models = self.list()
        return [m for m in models if all(m.get(k) == v for k, v in criteria.items())]
