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
