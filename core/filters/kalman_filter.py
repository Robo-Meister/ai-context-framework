import numpy as np

from interfaces.filter_strategy import FilterStrategy


class KalmanFilter(FilterStrategy):
    def __init__(self, dim):
        self.x = np.zeros((dim, 1))     # State estimate
        self.P = np.eye(dim)            # Covariance estimate
        self.Q = np.eye(dim) * 0.01     # Process noise
        self.R = np.eye(dim) * 0.1      # Measurement noise

    def apply(self, z):
        z = z.reshape(-1, 1)
        # Predict
        x_pred = self.x
        P_pred = self.P + self.Q
        # Update
        K = P_pred @ np.linalg.inv(P_pred + self.R)
        self.x = x_pred + K @ (z - x_pred)
        self.P = (np.eye(len(K)) - K) @ P_pred
        return self.x.flatten()
