import json
from datetime import datetime, timedelta

import pytest

from caiengine.objects.context_query import ContextQuery
from caiengine.pipelines.svg_layer_actions import SvgActionPlanner
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


def _ingest_basic_asset(provider):
    now = datetime.utcnow()
    provider.ingest_context(
        {
            "name": "characters/hero",
            "path": "characters/hero.svg",
            "summary": "Hero base asset",
            "layers": [
                {
                    "id": "pose-1",
                    "purpose": "Hero base pose",
                    "aliases": ["default_pose"],
                }
            ],
        },
        timestamp=now,
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


def test_svg_layer_pipeline_passes_canvas_and_constraints():
    provider = MemoryContextProvider()
    window = _query_window()
    _ingest_basic_asset(provider)

    plan = {"layers": []}
    engine = RecordingEngine(plan)
    pipeline = SvgLayerPipeline(provider, engine)

    canvas = {"width": 1024, "height": 768}
    constraints = {"max_layers": 5}

    pipeline.generate(
        "Compose hero portrait",
        window,
        canvas=canvas,
        constraints=constraints,
    )

    assert engine.last_input["canvas"] == canvas
    assert engine.last_input["constraints"] == constraints


def test_svg_layer_pipeline_rejects_empty_plan_string():
    provider = MemoryContextProvider()
    window = _query_window()
    _ingest_basic_asset(provider)

    engine = RecordingEngine("   ")
    pipeline = SvgLayerPipeline(provider, engine)

    with pytest.raises(ValueError) as exc:
        pipeline.generate("Invalid plan", window)

    assert "empty plan string" in str(exc.value)


def test_svg_layer_pipeline_rejects_invalid_json_plan():
    provider = MemoryContextProvider()
    window = _query_window()
    _ingest_basic_asset(provider)

    engine = RecordingEngine({"result": "{not json}"})
    pipeline = SvgLayerPipeline(provider, engine)

    with pytest.raises(ValueError) as exc:
        pipeline.generate("Invalid json", window)

    assert "invalid JSON plan" in str(exc.value)


def test_svg_layer_pipeline_end_to_end_layer_actions(tmp_path):
    provider = MemoryContextProvider()
    window = _query_window()

    asset_dir = tmp_path / "characters"
    asset_dir.mkdir()
    svg_path = asset_dir / "hero.svg"
    svg_path.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <g id="pose">
                <rect x="10" y="10" width="30" height="80" fill="#ff0000" />
            </g>
            <g id="shadow">
                <ellipse cx="40" cy="90" rx="30" ry="8" fill="#00000055" />
            </g>
        </svg>
        """.strip(),
        encoding="utf-8",
    )

    now = datetime.utcnow()
    provider.ingest_context(
        {
            "name": "characters/hero",
            "path": "characters/hero.svg",
            "summary": "Hero figure with shadow",
            "layers": [
                {"id": "pose", "purpose": "Primary silhouette"},
                {"id": "shadow", "purpose": "Cast shadow"},
            ],
            "bounding_boxes": {
                "pose": [10, 10, 40, 90],
                "shadow": [10, 82, 70, 98],
            },
        },
        timestamp=now,
        metadata={"roles": ["visual_assets"]},
    )

    plan_payload = {
        "plan": {
            "layers": [
                {
                    "layer_id": "pose-layer",
                    "source": "characters/hero.svg#pose",
                    "translate": [5, -2],
                    "opacity": 0.95,
                },
                {
                    "layer_id": "shadow-layer",
                    "source": "characters/hero.svg#shadow",
                    "scale": [1.1, 1.0],
                    "opacity": 0.6,
                },
            ]
        }
    }

    engine = RecordingEngine(plan_payload)
    pipeline = SvgLayerPipeline(provider, engine)
    result = pipeline.generate("Compose hero with shadow", window)

    validated_layers = result["plan"]["layers"]
    assert len(validated_layers) == 2
    assert {layer["fragment_id"] for layer in validated_layers} == {"pose", "shadow"}

    fetch_map = {"characters/hero.svg": svg_path}

    def fetch_asset(path: str) -> str:
        return fetch_map[path].read_text(encoding="utf-8")

    planner = SvgActionPlanner(asset_fetcher=fetch_asset)
    actions = planner.build_actions(result["plan"], result["assets"])

    assert len(actions) == 2
    assert all(action["action"] == "add" for action in actions)
    assert all("svg_content" in action["asset"] for action in actions)

    composed_svg = "<svg>" + "".join(
        f"<g id='{action['layer_id']}' data-fragment='{action['asset']['fragment_id']}'></g>"
        for action in actions
    ) + "</svg>"

    assert "pose-layer" in composed_svg
    assert "shadow-layer" in composed_svg
