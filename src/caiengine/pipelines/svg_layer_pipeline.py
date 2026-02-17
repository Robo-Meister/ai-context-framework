from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from caiengine.common import AuditLogger
from caiengine.interfaces.context_provider import ContextProvider
from caiengine.interfaces.inference_engine import InferenceEngineInterface
from caiengine.objects.context_query import ContextQuery


@dataclass
class _NormalizedAsset:
    """Container that keeps track of SVG asset metadata for prompting."""

    name: str
    summary: str
    path: Optional[str]
    layers: Dict[str, Dict[str, Any]]
    palette_tokens: List[str]
    bounding_boxes: Dict[str, Any]
    identifiers: Tuple[str, ...]
    layer_aliases: Dict[str, str]
    raw: Dict[str, Any]

    def to_prompt_packet(self) -> Dict[str, Any]:
        """Return a JSON-friendly payload for the inference engine."""

        layers_payload: List[Dict[str, Any]] = []
        for layer_id, layer in self.layers.items():
            layer_payload = dict(layer)
            layer_payload.setdefault("id", layer_id)
            layers_payload.append(layer_payload)
        return {
            "summary": self.summary,
            "path": self.path,
            "layers": layers_payload,
            "palette_tokens": list(self.palette_tokens),
            "bounding_boxes": dict(self.bounding_boxes),
        }

    def to_manifest(self) -> Dict[str, Any]:
        """Return structured metadata for downstream automation layers."""

        manifest_layers: List[Dict[str, Any]] = []
        for layer_id, layer in self.layers.items():
            manifest_layer = dict(layer)
            manifest_layer.setdefault("id", layer_id)
            manifest_layers.append(manifest_layer)
        return {
            "name": self.name,
            "summary": self.summary,
            "path": self.path,
            "layers": manifest_layers,
            "palette_tokens": list(self.palette_tokens),
            "bounding_boxes": dict(self.bounding_boxes),
            "identifiers": list(self.identifiers),
        }


class SvgLayerPipeline:
    """Generate a layered SVG composition plan from contextual asset metadata."""

    def __init__(
        self,
        asset_provider: ContextProvider,
        inference_engine: InferenceEngineInterface,
        *,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.provider = asset_provider
        self.engine = inference_engine
        self.audit_logger = audit_logger

    def generate(
        self,
        prompt: str,
        query: ContextQuery,
        *,
        canvas: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return a validated SVG layer plan for ``prompt``."""

        if self.audit_logger:
            self.audit_logger.log(
                "SvgLayerPipeline",
                "run_start",
                {"has_canvas": canvas is not None, "has_constraints": constraints is not None},
            )

        assets, asset_index = self._collect_assets(query)

        asset_payload = {
            name: asset.to_prompt_packet() for name, asset in assets.items()
        }

        engine_payload: Dict[str, Any] = {
            "prompt": prompt,
            "visual_assets": asset_payload,
        }
        if canvas is not None:
            engine_payload["canvas"] = canvas
        if constraints is not None:
            engine_payload["constraints"] = constraints

        raw_result = self.engine.predict(engine_payload)
        plan = self._extract_plan(raw_result)
        validated_plan, warnings = self._validate_layers(plan, asset_index)

        if self.audit_logger:
            self.audit_logger.log(
                "SvgLayerPipeline",
                "plan_validated",
                {"layers": len(validated_plan.get("layers", [])), "warnings": len(warnings)},
            )

        manifest_assets = {
            name: asset.to_manifest() for name, asset in assets.items()
        }

        return {
            "plan": validated_plan,
            "assets": manifest_assets,
            "warnings": warnings,
            "raw_result": raw_result,
        }

    def _collect_assets(
        self, query: ContextQuery
    ) -> Tuple[Dict[str, _NormalizedAsset], Dict[str, _NormalizedAsset]]:
        entries = self.provider.get_context(query)
        assets: Dict[str, _NormalizedAsset] = {}
        index: Dict[str, _NormalizedAsset] = {}
        for entry in entries:
            asset = self._normalise_asset(entry)
            assets[asset.name] = asset
            for identifier in asset.identifiers:
                index[identifier] = asset
        return assets, index

    def _normalise_asset(self, entry: Dict[str, Any]) -> _NormalizedAsset:
        context = entry.get("context", {}) or {}
        metadata = entry.get("metadata", {}) or {}

        summary = (
            context.get("summary")
            or metadata.get("summary")
            or entry.get("content")
            or ""
        )
        name = (
            context.get("name")
            or metadata.get("name")
            or context.get("id")
            or metadata.get("id")
            or entry.get("id")
            or summary
        )
        path = context.get("path") or metadata.get("path")

        palette = context.get("palette_tokens")
        if palette is None:
            palette = context.get("palettes")
        if palette is None:
            palette = metadata.get("palette_tokens")
        palette_tokens = [p for p in (palette or []) if isinstance(p, str)]

        bounding_boxes = dict(context.get("bounding_boxes") or metadata.get("bounding_boxes") or {})

        layers = context.get("layers") or metadata.get("layers") or []
        layer_lookup: Dict[str, Dict[str, Any]] = {}
        layer_aliases: Dict[str, str] = {}
        for layer in layers:
            if not isinstance(layer, dict):
                continue
            layer_id = layer.get("id")
            if not isinstance(layer_id, str) or not layer_id:
                continue
            layer_lookup[layer_id] = dict(layer)
            aliases = layer.get("aliases") or []
            if isinstance(aliases, (list, tuple)):
                for alias in aliases:
                    if isinstance(alias, str) and alias:
                        layer_aliases[alias] = layer_id

        identifiers = set()
        for candidate in (
            name,
            path,
            context.get("id"),
            metadata.get("id"),
            context.get("slug"),
            metadata.get("slug"),
        ):
            if isinstance(candidate, str) and candidate:
                identifiers.add(candidate)
        for source in (context, metadata):
            for key in ("aliases", "identifiers"):
                alias_values = source.get(key)
                if isinstance(alias_values, (list, tuple)):
                    for alias in alias_values:
                        if isinstance(alias, str) and alias:
                            identifiers.add(alias)

        return _NormalizedAsset(
            name=name,
            summary=summary,
            path=path,
            layers=layer_lookup,
            palette_tokens=palette_tokens,
            bounding_boxes=bounding_boxes,
            identifiers=tuple(sorted(identifiers)),
            layer_aliases=layer_aliases,
            raw=entry,
        )

    def _extract_plan(self, raw_result: Any) -> Dict[str, Any]:
        plan_candidate: Any
        if isinstance(raw_result, dict):
            if "plan" in raw_result:
                plan_candidate = raw_result["plan"]
            elif "result" in raw_result:
                plan_candidate = raw_result["result"]
            else:
                plan_candidate = raw_result
        else:
            plan_candidate = raw_result

        if isinstance(plan_candidate, str):
            plan_candidate = plan_candidate.strip()
            if not plan_candidate:
                raise ValueError("Inference engine returned an empty plan string")
            try:
                plan = json.loads(plan_candidate)
            except json.JSONDecodeError as exc:
                raise ValueError("Inference engine returned an invalid JSON plan") from exc
        elif isinstance(plan_candidate, dict):
            plan = dict(plan_candidate)
        else:
            raise ValueError("Inference engine returned an unsupported plan payload")

        layers = plan.get("layers")
        if layers is None:
            plan["layers"] = []
        elif not isinstance(layers, list):
            raise ValueError("Layer plan must contain a list under the 'layers' key")
        return plan

    def _validate_layers(
        self,
        plan: Dict[str, Any],
        asset_index: Dict[str, _NormalizedAsset],
    ) -> Tuple[Dict[str, Any], List[str]]:
        warnings: List[str] = []
        validated_layers: List[Dict[str, Any]] = []

        for idx, layer in enumerate(plan.get("layers", [])):
            if not isinstance(layer, dict):
                warnings.append(f"Layer {idx} is not an object and was skipped")
                continue

            layer_copy = dict(layer)
            source = layer_copy.get("source")
            if not isinstance(source, str) or not source:
                warnings.append(f"Layer {idx} is missing a 'source' reference")
                continue

            asset_key, fragment = self._split_source(source)
            asset = asset_index.get(asset_key)
            if asset is None:
                warnings.append(f"Layer {idx} references unknown asset '{asset_key}'")
                continue

            canonical_fragment = self._resolve_fragment(asset, fragment)
            if fragment and canonical_fragment is None:
                warnings.append(
                    f"Layer {idx} references unknown fragment '{fragment}' for asset '{asset_key}'"
                )
                continue

            if canonical_fragment:
                layer_copy.setdefault("fragment_id", canonical_fragment)
                bbox = asset.bounding_boxes.get(canonical_fragment)
                if bbox is not None and "bounding_box" not in layer_copy:
                    layer_copy["bounding_box"] = bbox

            layer_copy.setdefault("asset_name", asset.name)
            if asset.path and "asset_path" not in layer_copy:
                layer_copy["asset_path"] = asset.path

            validated_layers.append(layer_copy)

        validated_plan = dict(plan)
        validated_plan["layers"] = validated_layers
        return validated_plan, warnings

    def _split_source(self, source: str) -> Tuple[str, Optional[str]]:
        base, sep, fragment = source.partition("#")
        if not sep:
            return source, None
        return base, fragment or None

    def _resolve_fragment(
        self, asset: _NormalizedAsset, fragment: Optional[str]
    ) -> Optional[str]:
        if fragment is None:
            return None
        if fragment in asset.layers:
            return fragment
        alias = asset.layer_aliases.get(fragment)
        if alias and alias in asset.layers:
            return alias
        return None
