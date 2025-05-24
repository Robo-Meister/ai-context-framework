import numpy as np


class FilterStrategy:
    def apply(self, vector: np.ndarray) -> np.ndarray:
        raise NotImplementedError()
