from typing import List

from interfaces.filter_strategy import FilterStrategy


class KalmanFilter(FilterStrategy):
    def __init__(self, dim: int):
        # In testing environments without numpy we keep state simple
        self.dim = dim

    def apply(self, z: List[float]) -> List[float]:
        """Return the input vector unchanged as a stub implementation."""
        return list(z)
