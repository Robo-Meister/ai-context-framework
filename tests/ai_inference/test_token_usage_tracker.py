import importlib.util
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

# import DummyAIInferenceEngine
_dummy_spec = importlib.util.spec_from_file_location(
    "dummy_engine", ROOT_DIR / "src" / "caiengine" / "inference" / "dummy_engine.py"
)
_dummy_module = importlib.util.module_from_spec(_dummy_spec)
_dummy_spec.loader.exec_module(_dummy_module)
DummyAIInferenceEngine = _dummy_module.DummyAIInferenceEngine

# import TokenUsageTracker
_tracker_spec = importlib.util.spec_from_file_location(
    "token_usage_tracker", ROOT_DIR / "src" / "caiengine" / "inference" / "token_usage_tracker.py"
)
_tracker_module = importlib.util.module_from_spec(_tracker_spec)
_tracker_spec.loader.exec_module(_tracker_module)
TokenUsageTracker = _tracker_module.TokenUsageTracker


def test_usage_counted_on_infer():
    engine = TokenUsageTracker(DummyAIInferenceEngine())
    data = {"text": "hello world"}
    result = engine.infer(data)
    assert "usage" in result
    usage = result["usage"]
    assert usage["prompt_tokens"] > 0
    assert usage["completion_tokens"] > 0
    assert engine.usage["total_tokens"] == usage["total_tokens"]


def test_usage_accumulates_across_calls():
    engine = TokenUsageTracker(DummyAIInferenceEngine())
    engine.predict({"msg": "one two"})
    first_total = engine.usage["total_tokens"]
    engine.predict({"msg": "three four"})
    assert engine.usage["total_tokens"] > first_total
