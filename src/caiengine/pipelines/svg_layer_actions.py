"""Utilities for turning validated SVG (and related) plans into executable actions."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


def _default_asset_fetcher(path: str) -> str:
    """Return the contents of ``path``.

    The callable is split out primarily to keep :class:`SvgActionPlanner`
    focused on orchestration logic while making it easy to stub in tests.
    """

    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except UnicodeDecodeError:
        # Binary payloads (for example GLB 3D models) cannot be decoded as
        # UTF-8.  Fallback to returning a base64 encoded representation so the
        # caller still receives a serialisable string payload.
        with open(path, "rb") as handle:
            data = handle.read()
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:application/octet-stream;base64,{encoded}"


@dataclass
class SvgAssetLink:
    """Describe the asset fragment (or inline SVG) backing an action."""

    asset_name: Optional[str] = None
    asset_path: Optional[str] = None
    fragment_id: Optional[str] = None
    inline_svg: Optional[str] = None
    asset_type: Optional[str] = None
    inline_model: Optional[str] = None
    model_path: Optional[str] = None
    model_format: Optional[str] = None
    model_content: Optional[str] = None
    materials: Dict[str, Any] = field(default_factory=dict)
    textures: Dict[str, Any] = field(default_factory=dict)
    bounding_box: Optional[Any] = None
    layer_metadata: Dict[str, Any] = field(default_factory=dict)
    svg_content: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if self.asset_name is not None:
            payload["asset_name"] = self.asset_name
        if self.asset_path is not None:
            payload["asset_path"] = self.asset_path
        if self.fragment_id is not None:
            payload["fragment_id"] = self.fragment_id
        if self.inline_svg is not None:
            payload["inline_svg"] = self.inline_svg
        if self.asset_type is not None:
            payload["asset_type"] = self.asset_type
        if self.inline_model is not None:
            payload["inline_model"] = self.inline_model
        if self.model_path is not None:
            payload["model_path"] = self.model_path
        if self.model_format is not None:
            payload["model_format"] = self.model_format
        if self.model_content is not None:
            payload["model_content"] = self.model_content
        if self.materials:
            payload["materials"] = dict(self.materials)
        if self.textures:
            payload["textures"] = dict(self.textures)
        if self.bounding_box is not None:
            payload["bounding_box"] = self.bounding_box
        if self.layer_metadata:
            payload["layer_metadata"] = dict(self.layer_metadata)
        if self.svg_content is not None:
            payload["svg_content"] = self.svg_content
        return payload


@dataclass
class SvgLayerAction:
    """Represent a single manipulation that should be applied to an SVG layer."""

    action: str
    layer_id: Optional[str] = None
    asset: Optional[SvgAssetLink] = None
    transforms: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"action": self.action}
        if self.layer_id is not None:
            payload["layer_id"] = self.layer_id
        if self.asset is not None:
            payload["asset"] = self.asset.to_payload()
        if self.transforms:
            payload["transforms"] = dict(self.transforms)
        if self.parameters:
            payload["parameters"] = dict(self.parameters)
        return payload


class SvgActionPlanner:
    """Transform validated layer plans into actionable SVG edit commands."""

    _TRANSFORM_KEYS = {
        "transform",
        "translate",
        "scale",
        "rotate",
        "rotation",
        "resize",
        "position",
        "skew",
        "orientation",
        "quaternion",
        "scale3d",
        "pivot",
    }

    _ASSET_KEYS = {
        "asset_name",
        "asset_path",
        "fragment_id",
        "source",
        "new_svg",
        "inline_svg",
        "svg",
        "model_path",
        "inline_model",
        "model",
        "model_format",
        "asset_type",
    }

    def __init__(
        self,
        *,
        asset_fetcher: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._asset_fetcher = asset_fetcher or _default_asset_fetcher

    def build_actions(
        self,
        plan: Dict[str, Any],
        assets: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Return a serialisable list of layer actions for ``plan``.

        Parameters
        ----------
        plan:
            Validated plan emitted by :class:`SvgLayerPipeline`.
        assets:
            Manifest payload from the same pipeline run used to resolve layer
            metadata and bounding boxes.
        """

        actions: List[SvgLayerAction] = []
        for layer in plan.get("layers", []):
            if not isinstance(layer, dict):
                continue

            action_type = self._determine_action(layer)
            layer_id = self._resolve_layer_id(layer)
            asset_link = self._build_asset_link(layer, assets)
            transforms = self._extract_transforms(layer)
            parameters = self._extract_parameters(layer)

            actions.append(
                SvgLayerAction(
                    action=action_type,
                    layer_id=layer_id,
                    asset=asset_link,
                    transforms=transforms,
                    parameters=parameters,
                )
            )

        return [action.to_payload() for action in actions]

    def _determine_action(self, layer: Dict[str, Any]) -> str:
        explicit = layer.get("operation") or layer.get("action")
        if isinstance(explicit, str) and explicit:
            return explicit

        if layer.get("remove") is True:
            return "remove"

        if self._contains_asset_reference(layer):
            # New fragments imply an add/replace operation. Default to add for
            # clarity and let downstream tooling decide whether this should
            # replace an existing layer based on ``layer_id``.
            return "add"

        if any(key in layer for key in self._TRANSFORM_KEYS):
            return "transform"

        # Fallback to update so metadata-only tweaks (e.g. z-index) are not
        # silently dropped.
        return "update"

    def _contains_asset_reference(self, layer: Dict[str, Any]) -> bool:
        if any(layer.get(key) for key in self._ASSET_KEYS):
            return True
        source = layer.get("source")
        return isinstance(source, str) and bool(source.strip())

    def _resolve_layer_id(self, layer: Dict[str, Any]) -> Optional[str]:
        for key in ("layer_id", "id", "name", "fragment_id"):
            value = layer.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _build_asset_link(
        self,
        layer: Dict[str, Any],
        assets: Dict[str, Dict[str, Any]],
    ) -> Optional[SvgAssetLink]:
        inline_svg = layer.get("new_svg") or layer.get("inline_svg") or layer.get("svg")
        inline_model = layer.get("inline_model") or layer.get("model")
        model_path = layer.get("model_path")
        model_format = layer.get("model_format")
        asset_type = layer.get("asset_type")

        is_model_layer = False
        if inline_model or model_path:
            is_model_layer = True
        elif isinstance(asset_type, str) and "3d" in asset_type.lower():
            is_model_layer = True

        asset_name = layer.get("asset_name")
        asset_path = layer.get("asset_path")
        fragment_id = layer.get("fragment_id")

        if not asset_name and not asset_path:
            source = layer.get("source")
            if isinstance(source, str) and source:
                asset_path, _, fragment_candidate = source.partition("#")
                fragment_id = fragment_id or (fragment_candidate or None)
                asset_name = self._resolve_asset_name_from_path(assets, asset_path)

        if is_model_layer and model_path and not asset_path:
            asset_path = model_path

        asset_name = asset_name or self._resolve_asset_name_from_path(assets, asset_path)
        manifest = assets.get(asset_name) if asset_name else None

        bounding_box = layer.get("bounding_box")
        layer_metadata: Dict[str, Any] = {}
        if manifest:
            bounding_box = bounding_box or manifest.get("bounding_boxes", {}).get(fragment_id)
            for entry in manifest.get("layers", []):
                if entry.get("id") == fragment_id:
                    layer_metadata = dict(entry)
                    break

        if is_model_layer and not model_format and model_path:
            model_format = self._infer_model_format(model_path)

        if not any((asset_name, asset_path, inline_svg, inline_model)):
            return None

        svg_content: Optional[str] = None
        model_content: Optional[str] = None
        if is_model_layer and model_path and self._asset_fetcher:
            try:
                model_content = self._asset_fetcher(model_path)
            except FileNotFoundError:
                model_content = None
            except OSError:
                model_content = None
        elif asset_path and self._asset_fetcher and not is_model_layer:
            try:
                svg_content = self._asset_fetcher(asset_path)
            except FileNotFoundError:
                svg_content = None
            except OSError:
                svg_content = None

        materials = layer.get("materials")
        if not isinstance(materials, dict):
            materials = {}
        textures = layer.get("textures")
        if not isinstance(textures, dict):
            textures = {}

        asset_type_payload = asset_type
        if is_model_layer and not asset_type_payload:
            asset_type_payload = "3d_model"

        return SvgAssetLink(
            asset_name=asset_name,
            asset_path=asset_path,
            fragment_id=fragment_id,
            inline_svg=inline_svg,
            asset_type=asset_type_payload,
            inline_model=inline_model,
            model_path=model_path,
            model_format=model_format,
            model_content=model_content,
            materials=materials,
            textures=textures,
            bounding_box=bounding_box,
            layer_metadata=layer_metadata,
            svg_content=svg_content,
        )

    def _resolve_asset_name_from_path(
        self, assets: Dict[str, Dict[str, Any]], asset_path: Optional[str]
    ) -> Optional[str]:
        if not asset_path:
            return None
        for name, manifest in assets.items():
            if manifest.get("path") == asset_path:
                return manifest.get("name") or name
        return None

    def _extract_transforms(self, layer: Dict[str, Any]) -> Dict[str, Any]:
        transforms: Dict[str, Any] = {}
        for key in self._TRANSFORM_KEYS:
            if key in layer:
                transforms[key] = layer[key]
        return transforms

    def _extract_parameters(self, layer: Dict[str, Any]) -> Dict[str, Any]:
        ignored = set(self._TRANSFORM_KEYS) | self._ASSET_KEYS | {
            "layer_id",
            "id",
            "name",
            "fragment_id",
            "operation",
            "action",
            "remove",
            "bounding_box",
            "model_content",
            "materials",
            "textures",
        }
        return {key: value for key, value in layer.items() if key not in ignored}

    def _infer_model_format(self, path: str) -> Optional[str]:
        suffix = Path(path).suffix
        if not suffix:
            return None
        formatted = suffix.lstrip(".").lower()
        return formatted or None


def build_svg_action_plan(
    plan: Dict[str, Any],
    assets: Dict[str, Dict[str, Any]],
    *,
    asset_fetcher: Optional[Callable[[str], str]] = None,
) -> List[Dict[str, Any]]:
    """Convenience wrapper around :class:`SvgActionPlanner` for scripts."""

    planner = SvgActionPlanner(asset_fetcher=asset_fetcher)
    return planner.build_actions(plan, assets)

