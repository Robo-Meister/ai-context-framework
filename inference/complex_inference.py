from sympy.printing.pytorch import torch

from core.learning.complex_net import ComplexNet
from interfaces.inference_engine import AIInferenceEngine


class ComplexAIInferenceEngine(AIInferenceEngine):
    def __init__(self, input_size, hidden_size=16, output_size=1):
        self.model = ComplexNet(input_size, hidden_size, output_size)

    def infer(self, input_data: dict) -> dict:
        # Convert input dict to tensor (you decide input format)
        x = self._preprocess(input_data)
        y_pred = self.model(x)
        return {"prediction": y_pred.item(), "confidence": 1.0}

    def predict(self, input_data: dict) -> dict:
        return self.infer(input_data)

    def train(self, input_data: dict, target: float) -> float:
        # Implement training loop or forward call here
        loss = self._train_step(input_data, target)
        return loss

    def _preprocess(self, input_data):
        # Convert dict to tensor, e.g. torch.tensor([...])
        pass

    def _train_step(self, input_data, target):
        # One step of training returning loss float
        pass

    def get_model(self):
        return self.model
