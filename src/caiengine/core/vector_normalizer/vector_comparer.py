# vector_comparer.py
import numpy as np

class VectorComparer:
    def __init__(self, weights: list = None):
        self.weights = weights

    def cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        a = self._weighted(vec_a)
        b = self._weighted(vec_b)

        dot = float(np.dot(a, b))
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def euclidean_distance(self, vec_a: list, vec_b: list) -> float:
        a = self._weighted(vec_a)
        b = self._weighted(vec_b)
        return float(np.linalg.norm(a - b))

    def _weighted(self, vec: list) -> np.ndarray:
        v = np.asarray(vec, dtype=float)
        if self.weights is None:
            return v
        w = np.asarray(self.weights, dtype=float)
        return v * w
