class ContextProvider:
    def __init__(self):
        # Weights sum to 1.0
        self.context_weights = {
            "role": 0.18,
            "environment": 0.18,
            "network": 0.12,
            "input": 0.12,
            "timeframe": 0.1,
            "mood": 0.08,
            "label": 0.1,  # Optional but powerful
            "device": 0.06,
            "location": 0.06,
        }

    def calculate_trust(self, context_data: dict) -> float:
        present_sum = 0.0
        total_weight = sum(self.context_weights.values())

        for layer, weight in self.context_weights.items():
            presence = 1 if context_data.get(layer) else 0
            present_sum += weight * presence

        return present_sum / total_weight if total_weight else 0.0

    def get_adjusted_weight(self, base_weight: float, context_data: dict) -> float:
        trust_score = self.calculate_trust(context_data)
        return base_weight * trust_score
