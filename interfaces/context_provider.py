class ContextProvider:
    def __init__(self):
        self.context_weights = {
            "role": 0.2,
            "environment": 0.2,
            "network": 0.15,
            "input": 0.15,
            "timeframe": 0.1,
            "mood": 0.1,
            "label": 0.1  # Optional but powerful
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
