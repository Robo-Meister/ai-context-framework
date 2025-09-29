from collections.abc import Iterable

from caiengine.interfaces.filter_strategy import FilterStrategy


class MinMaxFilter(FilterStrategy):
    """Clamp numeric values within a specified range."""

    def __init__(self, min_value: float, max_value: float):
        self.min_value = min_value
        self.max_value = max_value

    def apply(self, data):
        def _clamp(value: float) -> float:
            return max(self.min_value, min(self.max_value, float(value)))

        if isinstance(data, list):
            return [_clamp(v) for v in data]
        if isinstance(data, tuple):
            return tuple(_clamp(v) for v in data)
        if isinstance(data, Iterable) and not isinstance(data, (str, bytes)):
            return [_clamp(v) for v in data]
        return _clamp(data)
