# inference/dummy_engine.py

from caiengine.interfaces.inference_engine import AIInferenceEngine

class DummyAIInferenceEngine(AIInferenceEngine):
    def infer(self, input_data: dict) -> dict:
        return {
            "result": "ok",
            "input_echo": input_data,
            "confidence": 0.5
        }

    def predict(self, input_data: dict) -> dict:
        # Forward to infer or implement simplified logic
        return self.infer(input_data)

    def train(self, input_data: dict, target: float) -> float:
        # No training, just return 0 loss
        return 0.0

    def replace_model(self, model, lr: float):
        # Dummy engine has no model to replace
        pass

    def save_model(self, path: str):
        # Nothing to save for the dummy engine
        pass

    def load_model(self, path: str):
        # Nothing to load for the dummy engine
        pass
