from core.vector_normalizer.context_encoder import ContextEncoder
from core.vector_normalizer.vector_comparer import VectorComparer
from typing import List, Dict, Tuple
from core.trust_module import TrustModule


class FullVectorComparer:
    """Compare full context dictionaries using vector encoding and trust weight."""

    def __init__(self, weights: List[float] | None = None,
                 encoder: ContextEncoder | None = None,
                 trust_module: TrustModule | None = None):
        self.encoder = encoder or ContextEncoder()
        self.vector_comparer = VectorComparer(weights=weights)
        self.trust_module = trust_module

    def _trust_score(self, context: Dict) -> float:
        if not self.trust_module:
            return 1.0
        presence = {k: bool(v) for k, v in context.items()}
        return self.trust_module.calculate_trust(presence)

    def compare(self, ctx_a: Dict, ctx_b: Dict) -> float:
        """Return similarity score between two contexts."""
        vec_a = self.encoder.encode(ctx_a)
        vec_b = self.encoder.encode(ctx_b)
        base = self.vector_comparer.cosine_similarity(vec_a, vec_b)
        trust = (self._trust_score(ctx_a) + self._trust_score(ctx_b)) / 2
        return base * trust

    def compare_batch(self, contexts: List[Dict]) -> Dict[Tuple[int, int], float]:
        """Compare each pair of contexts and return similarity matrix."""
        results: Dict[Tuple[int, int], float] = {}
        for i in range(len(contexts)):
            for j in range(i + 1, len(contexts)):
                results[(i, j)] = self.compare(contexts[i], contexts[j])
        return results
