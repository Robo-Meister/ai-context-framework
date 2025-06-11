import numpy as np

from interfaces.filter_strategy import FilterStrategy


class KalmanFilter(FilterStrategy):
    """Simple Kalman filter implementation using NumPy arrays."""

    def __init__(self, dim: int, process_var: float = 1e-2, measurement_var: float = 1e-1):
        self.x = np.zeros(dim)
        self.P = np.eye(dim)
        self.Q = np.eye(dim) * process_var
        self.R = np.eye(dim) * measurement_var
        self.initialized = False

    def apply(self, z: np.ndarray) -> np.ndarray:
        z = np.asarray(z, dtype=float)
        if not self.initialized:
            self.x = z
            self.initialized = True
            return self.x.copy()

        self.P = self.P + self.Q
        K = self.P @ np.linalg.inv(self.P + self.R)
        self.x = self.x + K @ (z - self.x)
        self.P = (np.eye(len(self.x)) - K) @ self.P
        return self.x.copy()
