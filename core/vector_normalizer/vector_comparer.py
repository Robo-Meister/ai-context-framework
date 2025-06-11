# vector_comparer.py
import math

class VectorComparer:
    def __init__(self, weights: list = None):
        self.weights = weights

    def cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        a = self._weighted(vec_a)
        b = self._weighted(vec_b)

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def euclidean_distance(self, vec_a: list, vec_b: list) -> float:
        a = self._weighted(vec_a)
        b = self._weighted(vec_b)
        diff = [x - y for x, y in zip(a, b)]
        return math.sqrt(sum(d * d for d in diff))

    def _weighted(self, vec: list) -> list:
        if not self.weights:
            return list(vec)
        return [v * w for v, w in zip(vec, self.weights)]
