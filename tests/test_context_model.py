import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "context_model",
    Path(__file__).resolve().parents[1]
    / "src"
    / "caiengine"
    / "common"
    / "context_model.py",
)
context_model = importlib.util.module_from_spec(spec)
sys.modules["context_model"] = context_model
spec.loader.exec_module(context_model)
Event = context_model.Event
ContextCategory = context_model.ContextCategory
ContextLayer = context_model.ContextLayer


def test_save_and_load_event(tmp_path):
    layer = ContextLayer(
        layer_id="layer1",
        data={"key": "value"},
        weight=0.5,
        trust=0.9,
    )
    category = ContextCategory(name="user", layers=[layer])
    event = Event(
        event_id="evt-123",
        timestamp=1710000000.0,
        source="sensor",
        payload={"foo": "bar"},
        contexts={"user": category},
    )

    path = tmp_path / "event.json"
    event.save(path)
    loaded = Event.load(path)
    assert loaded == event
