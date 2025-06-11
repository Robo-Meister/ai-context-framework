from typing import Dict, List, Optional, Any
import numpy as np

class TrustModule:
    def __init__(self, weights: Dict[str, float], distance_method: str = "cosine", parser=None):
        """
        weights: dict mapping context layer names to weights
        distance_method: one of 'cosine', 'euclidean' (expandable)
        """
        self.weights = weights
        self.distance_method = distance_method
        self.memory = []  # list of trusted contexts (dicts)
        self.parser = parser  # <-- store parser instance here

    def calculate_trust(self, context: Dict[str, bool], required_layers: Optional[List[str]] = None) -> float:
        """
        Calculate trust score based on presence of weighted layers.
        context: dict of {layer_name: bool} indicating presence
        """
        if required_layers is None:
            required_layers = []
        present_score = sum(self.weights.get(layer, 0) for layer in context if context[layer] and layer in self.weights)
        total_score = sum(self.weights[layer] for layer in self.weights)
        # Optionally penalize if required layers are missing
        for layer in required_layers:
            if not context.get(layer, False):
                present_score -= self.weights.get(layer, 0)
        return max(0.0, present_score / total_score) if total_score > 0 else 0.0

    def compare_contexts(self, ctx1: Dict[str, float], ctx2: Dict[str, float]) -> float:
        """
        Compare two contexts represented as dicts of feature scores.
        Returns similarity score in [0,1]
        """
        # Convert to vectors aligned by keys
        keys = sorted(set(ctx1.keys()) | set(ctx2.keys()))
        v1 = np.array([ctx1.get(k, 0.0) for k in keys], dtype=float)
        v2 = np.array([ctx2.get(k, 0.0) for k in keys], dtype=float)

        if self.distance_method == "cosine":
            dot_val = float(np.dot(v1, v2))
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return dot_val / (norm1 * norm2)

        elif self.distance_method == "euclidean":
            dist = np.linalg.norm(v1 - v2)
            max_dist = np.sqrt(len(keys))
            return max(0.0, 1 - dist / max_dist)

        else:
            raise ValueError(f"Unsupported distance method: {self.distance_method}")

    def add_to_memory(self, context: Dict[str, float]):
        """
        Store a trusted context into memory for future comparison
        """
        self.memory.append(context)

    def load_examples(self, examples: List[Dict[str, float]]):
        """Load multiple trusted contexts at once."""
        self.memory.extend(examples)

    def get_max_similarity(self, context: Dict[str, float]) -> float:
        """
        Compare given context against all in memory and return max similarity score
        """
        if not self.memory:
            return 0.0
        scores = [self.compare_contexts(context, mem_ctx) for mem_ctx in self.memory]
        return max(scores)

    def compute_trust_with_memory(self, context_presence: Dict[str, bool], context_scores: Dict[str, float],
                                  required_layers: Optional[List[str]] = None) -> float:
        """
        Combine layer presence trust and similarity with memory contexts
        """
        base_trust = self.calculate_trust(context_presence, required_layers)
        max_sim = self.get_max_similarity(context_scores)

        # Combine with weighted formula: trust = base_trust * (1 - distance)
        # Here similarity is like (1 - distance), so we can combine multiplicatively or additively
        combined_trust = base_trust * max_sim
        return combined_trust

    def extract_numeric_features(self, context: Dict[str, Any]) -> List[float]:
        # Turn context into numeric vector
        timestamp_score = context.get('timestamp').timestamp() % 86400 / 86400 if context.get('timestamp') else 0.5
        role_score = len(context.get('roles', [])) / 3.0  # Max 3 known roles
        situation_score = len(context.get('situations', [])) / 5.0  # Includes log level
        content_length = len(context.get('content', '')) / 100.0

        return [timestamp_score, role_score, situation_score, content_length]

    def extract_features_and_score(self, log_line: str) -> (List[float], float):
        if self.parser is None:
            raise ValueError("Parser is not set in TrustModule")

        context = self.parser.transform(log_line)  # Use the parser to get context
        features = self.extract_numeric_features(context)
        return features, context['score']
    def extract_features(self, context: dict) -> List[float]:
        return self.extract_numeric_features(context)
