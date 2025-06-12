# vector_normalizer.py

class VectorNormalizer:
    def __init__(self):
        self.time_map = {
            "morning": 0.2,
            "before lunch": 0.3,
            "afternoon": 0.6,
            "evening": 0.8,
            "night": 1.0
        }

        self.space_map = {
            "around the house": [0.1, 0.2],
            "at office": [0.5, 0.6],
            "warehouse": [0.8, 0.9]
        }

        self.role_map = {
            "admin": 1.0,
            "user": 0.5,
            "guest": 0.2
        }

        self.label_map = {
            "invoice": [1, 0, 0],
            "task": [0, 1, 0],
            "report": [0, 0, 1]
        }

        self.mood_map = {
            "happy": 0.1,
            "neutral": 0.5,
            "stressed": 0.9
        }

        self.default_space = [0.0, 0.0]
        self.default_label = [0.0, 0.0, 0.0]

    def normalize(self, context: dict) -> list:
        vector = []

        # Time: single float
        vector.append(self.time_map.get(context.get("time"), 0.0))

        # Space: 2D vector
        vector.extend(self.space_map.get(context.get("space"), self.default_space))

        # Role: single float
        vector.append(self.role_map.get(context.get("role"), 0.0))

        # Label: 3D one-hot or soft-class
        vector.extend(self.label_map.get(context.get("label"), self.default_label))

        # Mood: single float
        vector.append(self.mood_map.get(context.get("mood"), 0.0))

        # Network: hashed float
        vector.append(self.normalize_network(context.get("network")))

        return vector

    def normalize_network(self, node_id: str) -> float:
        if not node_id:
            return 0.0
        return float(abs(hash(node_id)) % 1000) / 1000.0
