import numpy as np


class FilterStrategy:
    def apply(self, vector: np.ndarray) -> np.ndarray:
        """Apply filter to a vector and return the filtered vector."""
        raise NotImplementedError()
