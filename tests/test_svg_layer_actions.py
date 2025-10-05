from __future__ import annotations

from typing import Dict, List

from caiengine.pipelines.svg_layer_actions import (
    SvgActionPlanner,
    build_svg_action_plan,
)


def _manifest() -> Dict[str, Dict[str, any]]:
    return {
        "characters/hero": {
            "name": "characters/hero",
            "path": "characters/hero.svg",
            "layers": [
                {"id": "pose-1", "purpose": "Hero base pose"},
                {"id": "shadow", "purpose": "Drop shadow"},
            ],
            "bounding_boxes": {"pose-1": [0, 0, 480, 960]},
        }
    }


def _plan_with_layers() -> Dict[str, List[dict]]:
    return {
        "layers": [
            {
                "layer_id": "hero_pose",
                "asset_name": "characters/hero",
                "asset_path": "characters/hero.svg",
                "fragment_id": "pose-1",
                "translate": [16, -8],
                "rotate": {"angle": 12},
                "opacity": 0.85,
            },
            {
                "layer_id": "hero_shadow",
                "asset_path": "characters/hero.svg",
                "fragment_id": "shadow",
                "operation": "transform",
                "scale": [1.1, 0.9],
                "skew": {"x": 5},
            },
            {
                "layer_id": "background",
                "operation": "remove",
            },
        ]
    }


def test_build_svg_action_plan_extracts_links_and_transforms(tmp_path):
    svg_path = tmp_path / "characters" / "hero.svg"
    svg_path.parent.mkdir(parents=True)
    svg_path.write_text("<svg id='hero'></svg>", encoding="utf-8")

    actions = build_svg_action_plan(
        _plan_with_layers(),
        _manifest(),
        asset_fetcher=lambda path: svg_path.read_text(encoding="utf-8"),
    )

    assert len(actions) == 3

    add_action = actions[0]
    assert add_action["action"] == "add"
    assert add_action["layer_id"] == "hero_pose"
    asset = add_action["asset"]
    assert asset["asset_path"] == "characters/hero.svg"
    assert asset["fragment_id"] == "pose-1"
    assert asset["bounding_box"] == [0, 0, 480, 960]
    assert "svg_content" in asset and "<svg" in asset["svg_content"]
    assert add_action["transforms"]["translate"] == [16, -8]
    assert add_action["parameters"]["opacity"] == 0.85

    transform_action = actions[1]
    assert transform_action["action"] == "transform"
    assert transform_action["asset"]["fragment_id"] == "shadow"
    assert transform_action["transforms"]["scale"] == [1.1, 0.9]
    assert transform_action["transforms"]["skew"] == {"x": 5}

    remove_action = actions[2]
    assert remove_action == {"action": "remove", "layer_id": "background"}


def test_action_planner_handles_inline_svg():
    planner = SvgActionPlanner(asset_fetcher=lambda path: "<svg></svg>")
    plan = {
        "layers": [
            {
                "layer_id": "new_overlay",
                "new_svg": "<svg id='overlay'></svg>",
                "position": {"x": 20, "y": 10},
                "z_index": 5,
            }
        ]
    }

    result = planner.build_actions(plan, {})
    assert result == [
        {
            "action": "add",
            "layer_id": "new_overlay",
            "asset": {
                "inline_svg": "<svg id='overlay'></svg>",
            },
            "transforms": {"position": {"x": 20, "y": 10}},
            "parameters": {"z_index": 5},
        }
    ]


def test_action_planner_defaults_to_update_for_metadata_changes():
    planner = SvgActionPlanner(asset_fetcher=lambda path: "<svg></svg>")
    plan = {"layers": [{"layer_id": "title", "visible": False}]}
    result = planner.build_actions(plan, {})

    assert result == [
        {
            "action": "update",
            "layer_id": "title",
            "parameters": {"visible": False},
        }
    ]


def test_action_planner_skips_non_dict_layers():
    planner = SvgActionPlanner(asset_fetcher=lambda path: "<svg></svg>")
    plan = {"layers": [{"layer_id": "valid", "remove": True}, "invalid"]}
    result = planner.build_actions(plan, {})

    assert result == [
        {
            "action": "remove",
            "layer_id": "valid",
        }
    ]

