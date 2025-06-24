import numpy as np
from caiengine.interfaces.filter_strategy import FilterStrategy


class MinMaxFilter(FilterStrategy):
    """Clamp numeric values within a specified range."""

    def __init__(self, min_value: float, max_value: float):
        self.min_value = min_value
        self.max_value = max_value

    def apply(self, data):
        arr = np.asarray(data, dtype=float)
        clipped = np.clip(arr, self.min_value, self.max_value)
        if isinstance(data, np.ndarray):
            return clipped
        elif isinstance(data, list):
            return clipped.tolist()
        else:
            return float(clipped)
