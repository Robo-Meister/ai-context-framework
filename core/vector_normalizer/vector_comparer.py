# vector_comparer.py
"""Utility for comparing numeric vectors without heavy dependencies."""

import math

class VectorComparer:
    def __init__(self, weights: list = None):
        self.weights = weights

    def cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        """Return the cosine similarity between two vectors."""
        a = self._weighted(vec_a)
        b = self._weighted(vec_b)

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def euclidean_distance(self, vec_a: list, vec_b: list) -> float:
        """Return the Euclidean distance between two vectors."""
        a = self._weighted(vec_a)
        b = self._weighted(vec_b)
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _weighted(self, vec: list) -> list:
        """Apply weights to a vector if provided."""
        if not self.weights:
            return list(vec)
        return [v * w for v, w in zip(vec, self.weights)]
