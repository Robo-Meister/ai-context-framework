"""Placeholder inference engine used for tests without heavy deps."""

from interfaces.inference_engine import AIInferenceEngine


class ComplexAIInferenceEngine(AIInferenceEngine):
    def __init__(self, input_size, hidden_size=16, output_size=1):
        self.model = None

    def infer(self, input_data: dict) -> dict:
        # Convert input dict to tensor (you decide input format)
        # Without a real model we just echo a dummy prediction.
        return {"prediction": 0.0, "confidence": 0.0}

    def predict(self, input_data: dict) -> dict:
        return self.infer(input_data)

    def train(self, input_data: dict, target: float) -> float:
        # Placeholder training step
        return 0.0

    def _preprocess(self, input_data):
        # Convert dict to tensor, e.g. torch.tensor([...])
        pass

    def _train_step(self, input_data, target):
        # One step of training returning loss float
        pass

    def get_model(self):
        return self.model
