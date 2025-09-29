from typing import List, Tuple
import math


class ANNIndex:
    """Simple wrapper around Annoy for approximate nearest neighbor search."""

    def __init__(self, vector_dim: int, metric: str = "euclidean"):
        self.vector_dim = vector_dim
        self.metric = metric
        self._items: List[Tuple[str, List[float]]] = []

    def add_item(self, item_id: str, vector: List[float]):
        if len(vector) != self.vector_dim:
            raise ValueError("Vector dimension mismatch")
        self._items.append((item_id, [float(v) for v in vector]))

    def build(self, n_trees: int = 10):
        # No-op for the lightweight in-memory implementation.
        return None

    def query(self, vector: List[float], k: int = 5) -> List[str]:
        if len(vector) != self.vector_dim:
            raise ValueError("Vector dimension mismatch")
        query_vec = [float(v) for v in vector]
        scored: List[Tuple[float, str]] = []
        for item_id, item_vec in self._items:
            if self.metric == "cosine":
                score = _cosine_distance(query_vec, item_vec)
            else:
                score = _euclidean_distance(query_vec, item_vec)
            scored.append((score, item_id))
        scored.sort(key=lambda x: x[0])
        return [item_id for _, item_id in scored[:k]]


def _euclidean_distance(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _cosine_distance(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 1.0
    cosine = max(-1.0, min(1.0, dot / (norm_a * norm_b)))
    return 1.0 - cosine
