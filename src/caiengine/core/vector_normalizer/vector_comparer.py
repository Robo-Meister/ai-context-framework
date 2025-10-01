from __future__ import annotations

import math
from itertools import zip_longest
from typing import Iterable, List

class VectorComparer:
    def __init__(self, weights: list | None = None):
        self.weights = list(weights) if weights is not None else None

    def cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        a, b = self._prepare_vectors(vec_a, vec_b)

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def euclidean_distance(self, vec_a: list, vec_b: list) -> float:
        a, b = self._prepare_vectors(vec_a, vec_b)
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _prepare_vectors(self, vec_a: Iterable[float], vec_b: Iterable[float]) -> tuple[List[float], List[float]]:
        list_a = [float(v) for v in vec_a]
        list_b = [float(v) for v in vec_b]
        if len(list_a) != len(list_b):
            raise ValueError("Vectors must be the same length")
        return self._weighted(list_a), self._weighted(list_b)

    def _weighted(self, vec: Iterable[float]) -> List[float]:
        values = [float(v) for v in vec]
        if self.weights is None:
            return values
        if len(self.weights) != len(values):
            raise ValueError("Weight vector must match value length")
        return [v * float(w) for v, w in zip_longest(values, self.weights, fillvalue=1.0)]
