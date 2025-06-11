from typing import List
from annoy import AnnoyIndex


class ANNIndex:
    """Simple wrapper around Annoy for approximate nearest neighbor search."""

    def __init__(self, vector_dim: int, metric: str = "euclidean"):
        self.vector_dim = vector_dim
        self.index = AnnoyIndex(vector_dim, metric)
        self.id_map: dict[int, str] = {}
        self._next = 0

    def add_item(self, item_id: str, vector: List[float]):
        self.index.add_item(self._next, vector)
        self.id_map[self._next] = item_id
        self._next += 1

    def build(self, n_trees: int = 10):
        self.index.build(n_trees)

    def query(self, vector: List[float], k: int = 5) -> List[str]:
        ids = self.index.get_nns_by_vector(vector, k)
        return [self.id_map[i] for i in ids]
