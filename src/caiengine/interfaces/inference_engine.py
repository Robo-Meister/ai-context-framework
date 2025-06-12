# inference/inference_engine.py

from abc import ABC, abstractmethod
from typing import Dict


class AIInferenceEngine(ABC):

    def infer(self, input_data: Dict) -> Dict:
        """
        Perform inference on input_data and return prediction results as dict.
        This is the main entry point for AI engines.
        """
        raise NotImplementedError("infer method must be implemented")

    @abstractmethod
    def predict(self, input_data: Dict) -> Dict:
        """
        Optional: A simplified prediction method.
        Default implementation delegates to infer().
        """
        return self.infer(input_data)

    def train(self, input_data: Dict, target: float) -> float:
        """
        Optional: Train the model using input_data and target label.
        Returns a loss value or metric.
        By default, training is unsupported.
        """
        raise NotImplementedError("train method not implemented for this engine")

    def replace_model(self, model, lr: float):
        """Optional: Replace the underlying model and optimizer."""
        raise NotImplementedError("replace_model not implemented for this engine")

    def save_model(self, path: str):
        """Optional: Persist the current model to ``path``."""
        raise NotImplementedError("save_model not implemented for this engine")

    def load_model(self, path: str):
        """Optional: Load model weights from ``path``."""
        raise NotImplementedError("load_model not implemented for this engine")
