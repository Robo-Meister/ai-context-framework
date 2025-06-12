class LearningInterface:
    def predict(self, input_data: dict) -> dict:
        pass

    def train(self, input_data: dict, target: float) -> float:
        pass

    def infer(self, input_data: dict) -> dict:
        """Perform inference from raw or fused input, possibly with more info."""
        pass
