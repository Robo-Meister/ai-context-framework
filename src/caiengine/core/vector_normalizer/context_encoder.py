import logging

from caiengine.core.vector_normalizer.vector_comparer import VectorComparer

logger = logging.getLogger(__name__)
class ContextEncoder:
    def __init__(self):
        self.time_map = {
            "morning": 0.2, "before lunch": 0.3, "afternoon": 0.6, "evening": 0.8, "night": 1.0
        }
        self.space_map = {
            "around the house": [0.1, 0.2], "at office": [0.5, 0.6], "warehouse": [0.8, 0.9]
        }
        self.role_map = {
            "admin": 1.0, "user": 0.5, "guest": 0.2
        }
        self.label_map = {
            "invoice": [1, 0, 0], "task": [0, 1, 0], "report": [0, 0, 1]
        }
        self.mood_map = {
            "happy": 0.1, "neutral": 0.5, "stressed": 0.9
        }
        self.default_space = [0.0, 0.0]
        self.default_label = [0.0, 0.0, 0.0]

    def encode(self, context: dict) -> list:
        vector = []
        vector.append(self.time_map.get(context.get("time"), 0.0))
        vector.extend(self.space_map.get(context.get("space"), self.default_space))
        vector.append(self.role_map.get(context.get("role"), 0.0))
        vector.extend(self.label_map.get(context.get("label"), self.default_label))
        vector.append(self.mood_map.get(context.get("mood"), 0.0))
        vector.append(self._hash_network(context.get("network")))
        return vector

    def _hash_network(self, node_id: str) -> float:
        if not node_id:
            return 0.0
        return float(abs(hash(node_id)) % 1000) / 1000.0

if __name__ == "__main__":
    encoder = ContextEncoder()
    comparer = VectorComparer(weights=[1.5, 1, 1, 1.3, 1.2, 1.2, 1.2, 0.8, 1.0])  # match vector length

    ctx1 = {
        "time": "morning",
        "space": "around the house",
        "role": "user",
        "label": "task",
        "mood": "neutral",
        "network": "node123"
    }

    ctx2 = {
        "time": "afternoon",
        "space": "at office",
        "role": "user",
        "label": "task",
        "mood": "neutral",
        "network": "node123"
    }

    vec1 = encoder.encode(ctx1)
    vec2 = encoder.encode(ctx2)

    logger.info("Cosine Similarity: %s", comparer.cosine_similarity(vec1, vec2))
    logger.info("Euclidean Distance: %s", comparer.euclidean_distance(vec1, vec2))
