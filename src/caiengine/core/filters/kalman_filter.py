from caiengine.interfaces.filter_strategy import FilterStrategy
from typing import List


class KalmanFilter(FilterStrategy):
    """Simple vector Kalman filter implementation without external deps."""

    def __init__(
        self, dim: int, process_var: float = 1e-2, measurement_var: float = 1e-1
    ):
        self.x = [0.0 for _ in range(dim)]
        self.P = [1.0 for _ in range(dim)]
        self.Q = [process_var for _ in range(dim)]
        self.R = [measurement_var for _ in range(dim)]
        self.initialized = False

    def apply(self, z):
        values = [float(v) for v in (z if isinstance(z, (list, tuple)) else [z])]
        if not self.initialized:
            self.x = values
            self.initialized = True
            return list(self.x) if isinstance(z, (list, tuple)) else self.x[0]

        updated: List[float] = []
        for i, measurement in enumerate(values):
            prev_x = self.x[i]
            prev_P = self.P[i] + self.Q[i]
            denom = prev_P + self.R[i]
            K = prev_P / denom if denom else 0.0
            estimate = prev_x + K * (measurement - prev_x)
            covariance = (1 - K) * prev_P
            updated.append(estimate)
            self.x[i] = estimate
            self.P[i] = covariance

        return updated if isinstance(z, (list, tuple)) else updated[0]
