from collections.abc import Iterable

from caiengine.interfaces.filter_strategy import FilterStrategy

try:  # pragma: no cover - numpy is optional at runtime
    import numpy as np
except Exception:  # pragma: no cover - keep previous behaviour when numpy missing
    np = None


class MinMaxFilter(FilterStrategy):
    """Clamp numeric values within a specified range."""

    def __init__(self, min_value: float, max_value: float):
        self.min_value = min_value
        self.max_value = max_value

    def apply(self, data):
        def _clamp(value: float) -> float:
            return max(self.min_value, min(self.max_value, float(value)))

        if _is_numpy_array(data):
            clipped = np.clip(data, self.min_value, self.max_value)
            return _maybe_copy_array(clipped)

        if isinstance(data, list):
            return [_clamp(v) for v in data]
        if isinstance(data, tuple):
            return tuple(_clamp(v) for v in data)
        if isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
            return [_clamp(v) for v in data]
        return _clamp(data)


def _is_numpy_array(value) -> bool:
    if np is None:
        return False

    ndarray = getattr(np, "ndarray", ())
    if ndarray and isinstance(value, ndarray):
        return True
    return hasattr(value, "__array__") and not isinstance(value, (list, tuple))


def _maybe_copy_array(value):
    """Return a copy when numpy provides ``clip`` returning views."""

    if np is None:
        return value

    if hasattr(value, "copy"):
        return value.copy()
    return value
