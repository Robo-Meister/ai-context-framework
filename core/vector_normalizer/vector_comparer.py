# vector_comparer.py
import numpy as np

class VectorComparer:
    def __init__(self, weights: list = None):
        self.weights = weights

    def cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        a = self._weighted(vec_a)
        b = self._weighted(vec_b)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def euclidean_distance(self, vec_a: list, vec_b: list) -> float:
        a = self._weighted(vec_a)
        b = self._weighted(vec_b)
        return np.linalg.norm(np.array(a) - np.array(b))

    def _weighted(self, vec: list) -> np.ndarray:
        if not self.weights:
            return np.array(vec)
        return np.array([v * w for v, w in zip(vec, self.weights)])
