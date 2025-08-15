from typing import Any

try:  # pragma: no cover - numpy is optional for simple filter strategy
    import numpy as np  # noqa: F401
except Exception:  # pragma: no cover - fallback when numpy missing
    np = None


class FilterStrategy:
    def apply(self, data: Any) -> Any:
        """Apply filter to data and return the filtered result."""
        raise NotImplementedError()
