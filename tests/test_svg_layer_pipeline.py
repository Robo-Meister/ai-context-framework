import json
from datetime import datetime, timedelta

from caiengine.objects.context_query import ContextQuery
from caiengine.pipelines.svg_layer_pipeline import SvgLayerPipeline
from caiengine.providers.memory_context_provider import MemoryContextProvider
from caiengine.interfaces.inference_engine import AIInferenceEngine


class RecordingEngine(AIInferenceEngine):
    def __init__(self, plan):
        self.plan = plan
        self.last_input = None

    def predict(self, input_data):
        self.last_input = input_data
        return self.plan


def _query_window():
    now = datetime.utcnow()
    return ContextQuery(
        roles=[],
        time_range=(now - timedelta(seconds=1), now + timedelta(seconds=1)),
        scope="visual_assets",
        data_type="svg",
    )


def test_svg_layer_pipeline_normalises_assets_and_validates_layers():
    provider = MemoryContextProvider()
    window = _query_window()

    now = datetime.utcnow()
    provider.ingest_context(
        {
            "name": "characters/hero",
            "path": "characters/hero.svg",
            "summary": "Hero base asset",
            "layers": [
                {"id": "pose-1", "purpose": "Hero base pose", "aliases": ["default_pose"]},
                {"id": "shadow", "purpose": "Drop shadow"},
            ],
            "palette_tokens": ["hero.body", "hero.cape"],
            "bounding_boxes": {"pose-1": [0, 0, 480, 960]},
        },
        timestamp=now,
        metadata={"roles": ["visual_assets"]},
    )
    provider.ingest_context(
        {
            "name": "backgrounds/city",
            "path": "backgrounds/city.svg",
            "summary": "City skyline background",
            "layers": [{"id": "base", "purpose": "Skyline"}],
        },
        timestamp=now,
        metadata={"roles": ["visual_assets"]},
    )

    plan = {
        "canvas": {"width": 1920, "height": 1080},
        "layers": [
            {"source": "characters/hero.svg#default_pose", "transform": "scale(1.1)"},
            {"source": "backgrounds/city.svg#base", "opacity": 0.9},
            {"source": "effects/sparkle.svg#burst", "blend": "screen"},
        ],
    }

    engine = RecordingEngine(plan)
    pipeline = SvgLayerPipeline(provider, engine)
    result = pipeline.generate(
        "Compose hero shot at dawn",
        window,
        canvas={"width": 1920, "height": 1080},
    )

    assert engine.last_input is not None
    assets_payload = engine.last_input["visual_assets"]
    assert "characters/hero" in assets_payload
    hero_layers = assets_payload["characters/hero"]["layers"]
    assert any(layer["id"] == "pose-1" for layer in hero_layers)

    validated_layers = result["plan"]["layers"]
    assert len(validated_layers) == 2  # Unknown asset filtered out
    first_layer = validated_layers[0]
    assert first_layer["fragment_id"] == "pose-1"
    assert first_layer["bounding_box"] == [0, 0, 480, 960]
    assert first_layer["asset_path"] == "characters/hero.svg"

    warnings = result["warnings"]
    assert warnings and "effects/sparkle.svg" in warnings[0]

    manifest = result["assets"]["characters/hero"]
    assert "pose-1" in {layer["id"] for layer in manifest["layers"]}


def test_svg_layer_pipeline_parses_string_payload():
    provider = MemoryContextProvider()
    window = _query_window()
    now = datetime.utcnow()
    provider.ingest_context(
        {
            "name": "effects/sun_glow",
            "path": "effects/sun_glow.svg",
            "summary": "Sunrise glow effect",
            "layers": [{"id": "burst", "purpose": "Radial gradient"}],
        },
        timestamp=now,
    )

    plan_dict = {"layers": [{"source": "effects/sun_glow.svg#burst"}]}
    engine = RecordingEngine({"result": json.dumps(plan_dict)})
    pipeline = SvgLayerPipeline(provider, engine)
    result = pipeline.generate("Add morning glow", window)

    assert result["plan"]["layers"][0]["asset_name"] == "effects/sun_glow"
