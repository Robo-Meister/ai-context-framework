from __future__ import annotations

import inspect
from datetime import datetime
from typing import Any

from caiengine.common import AuditLogger
from caiengine.objects.context_query import ContextQuery
from caiengine.orchestration import (
    ContextPacketCompiler,
    ExpertRegistry,
    ExpertRouter,
)


class OrchestratedPipeline:
    """Pipeline that compiles context and routes requests to registered experts."""

    def __init__(
        self,
        context_provider: Any,
        registry: ExpertRegistry,
        *,
        compiler: ContextPacketCompiler | None = None,
        router: ExpertRouter | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.provider = context_provider
        self.registry = registry
        self.compiler = compiler or ContextPacketCompiler()
        self.router = router or ExpertRouter(registry=registry)
        self.audit_logger = audit_logger

    def run(self, request: dict[str, Any], goal_context: dict[str, Any] | None = None) -> dict[str, Any]:
        goal_context = goal_context or {}

        if self.audit_logger:
            self.audit_logger.log("OrchestratedPipeline", "run_start", {"request_keys": sorted(request.keys())})

        query = self._build_query(request=request, goal_context=goal_context)
        retrieved_context = self._get_context(query)

        raw_context = {
            "retrieved": {"items": retrieved_context, "count": len(retrieved_context)},
            "goal": goal_context,
            "request": request,
        }
        required_layers = list(request.get("required_layers") or goal_context.get("required_layers") or ["retrieved.items"])
        optional_layers = list(request.get("optional_layers") or goal_context.get("optional_layers") or ["goal", "request"])
        budget = dict(goal_context.get("budget") or request.get("budget") or {})

        context_packet = self.compiler.compile(
            context=raw_context,
            required=required_layers,
            optional=optional_layers,
            budget=budget,
        )

        if self.audit_logger:
            self.audit_logger.log(
                "OrchestratedPipeline",
                "context_packet_compiled",
                {"selected_layers": list(context_packet.selected_layers.keys()), "omitted": context_packet.omitted_layers},
            )

        routed_goal_context = dict(goal_context)
        routed_goal_context["context_packet"] = context_packet.selected_layers
        routed_goal_context["context_packet_stats"] = context_packet.stats

        routed_response = self.router.route(
            request=request,
            goal_context=routed_goal_context,
            context_layers=list(context_packet.selected_layers.keys()),
        )

        telemetry = {
            "routing_decisions": {
                "request_category": request.get("category") or goal_context.get("category"),
                "request_scope": request.get("scope") or goal_context.get("scope"),
                "request_tags": list(request.get("tags") or []),
            },
            "selected_layers": list(context_packet.selected_layers.keys()),
            "chosen_experts": list(routed_response.get("selected_experts", [])),
            "confidences": [
                float(entry.get("confidence", 0.0))
                for entry in routed_response.get("debug", {}).get("all_results", [])
            ],
        }

        if self.audit_logger:
            self.audit_logger.log("OrchestratedPipeline", "route_complete", telemetry)

        return {
            "response": routed_response,
            "telemetry": telemetry,
            "context_packet": context_packet,
        }

    def _build_query(self, request: dict[str, Any], goal_context: dict[str, Any]) -> ContextQuery:
        roles = list(request.get("roles") or goal_context.get("roles") or [])
        scope = str(request.get("scope") or goal_context.get("scope") or "")
        data_type = str(request.get("data_type") or goal_context.get("data_type") or "")

        time_range = request.get("time_range") or goal_context.get("time_range")
        if isinstance(time_range, (tuple, list)) and len(time_range) == 2:
            start, end = time_range
        else:
            start, end = datetime.min, datetime.max

        return ContextQuery(
            roles=roles,
            time_range=(start, end),
            scope=scope,
            data_type=data_type,
            predicate=request.get("predicate") or goal_context.get("predicate"),
        )

    def _get_context(self, query: ContextQuery) -> list[dict[str, Any]]:
        get_context = self.provider.get_context
        signature = inspect.signature(get_context)

        if self._accepts_query(signature):
            return get_context(query)

        return get_context()

    @staticmethod
    def _accepts_query(signature: inspect.Signature) -> bool:
        for parameter in signature.parameters.values():
            if parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                return True
            if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                return True
        return False
