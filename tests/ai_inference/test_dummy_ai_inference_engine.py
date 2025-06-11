import importlib.util
import os
import pathlib
import sys
import pytest

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

MODULE_PATH = ROOT_DIR / "inference" / "dummy_engine.py"
spec = importlib.util.spec_from_file_location("dummy_engine", MODULE_PATH)
dummy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dummy_module)
DummyAIInferenceEngine = dummy_module.DummyAIInferenceEngine


def test_infer_returns_expected_structure():
    engine = DummyAIInferenceEngine()
    data = {"foo": "bar"}
    result = engine.infer(data)
    assert result["result"] == "ok"
    assert result["input_echo"] == data
    assert result["confidence"] == 0.5


def test_predict_delegates_to_infer():
    engine = DummyAIInferenceEngine()
    data = {"x": 1}
    assert engine.predict(data) == engine.infer(data)


def test_train_returns_zero():
    engine = DummyAIInferenceEngine()
    assert engine.train({}, 0.0) == 0.0


def test_optional_methods_noop(tmp_path):
    engine = DummyAIInferenceEngine()
    engine.replace_model(None, 0.1)
    path = tmp_path / "model.pt"
    engine.save_model(str(path))
    engine.load_model(str(path))
