import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch.nn")
from caiengine.inference.complex_inference import ComplexAIInferenceEngine


class TestComplexAIInferenceEngine:
    def test_training_improves_prediction(self):
        engine = ComplexAIInferenceEngine(input_size=3)
        data = {"features": [0.2, 0.1, -0.3]}
        target = 0.6

        pred_before = engine.predict(data)["prediction"].real
        loss_before = (pred_before - target) ** 2

        for _ in range(200):
            loss = engine.train(data, target)
            assert loss >= 0

        pred_after = engine.predict(data)["prediction"].real
        loss_after = (pred_after - target) ** 2

        assert loss_after < loss_before

    def test_prediction_keys(self):
        engine = ComplexAIInferenceEngine(input_size=2)
        output = engine.predict({"features": [0.1, 0.2]})
        assert set(output.keys()) == {"prediction", "confidence"}
