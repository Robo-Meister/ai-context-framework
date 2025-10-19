from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import (
    SimpleGoalFeedbackStrategy,
    PersonalityGoalFeedbackStrategy,
)
from caiengine.experimental.goal_strategies import MarketingGoalFeedbackStrategy
from caiengine.commands import COMMAND


class _SessionContextStore:
    """In-memory helper for managing session metadata and attempts."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        session = self._store.setdefault(
            session_id, {"metadata": {}, "attempts": {}}
        )
        return session

    def update_metadata(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        session = self.get_session(session_id)
        session["metadata"].update(updates)
        return session

    def increment_attempt(self, session_id: str, goal: str) -> int:
        session = self.get_session(session_id)
        attempts: Dict[str, int] = session.setdefault("attempts", {})
        attempts[goal] = attempts.get(goal, 0) + 1
        return attempts[goal]


class CAIBridge:
    """Simple bridge for running goal feedback with optional NPC personalities."""

    def __init__(
        self,
        goal_state: Optional[Dict] = None,
        personality: Optional[str] = None,
        one_direction_layers: Optional[List[str]] | None = None,
        workflow: str | None = None,
        marketing_config: Optional[Dict[str, Any]] = None,
        session_store: Optional[Any] = None,
    ) -> None:
        self.goal_state = goal_state or {}
        self._session_store = session_store or _SessionContextStore()
        self._connector_registry: Any | None = None
        self._persona_loader: Optional[Callable[[str], Dict[str, Any]]] = None
        self._active_persona: Optional[Dict[str, Any]] = None
        self._telemetry_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        strategy = None
        if personality:
            strategy = PersonalityGoalFeedbackStrategy(
                personality=personality,
                one_direction_layers=one_direction_layers or [],
            )
        elif one_direction_layers is not None:
            strategy = SimpleGoalFeedbackStrategy(one_direction_layers)
        elif (workflow or "").lower() == "marketing":
            strategy = MarketingGoalFeedbackStrategy(
                config=marketing_config,
                session_store=self._session_store,
                telemetry_hook=self._emit_telemetry,
            )

        self.feedback_loop = (
            GoalDrivenFeedbackLoop(strategy, goal_state=self.goal_state)
            if strategy
            else None
        )

    def suggest(self, history: List[Dict], actions: List[Dict]) -> List[Dict]:
        if self.feedback_loop:
            suggestions = self.feedback_loop.suggest(history, actions)
            self._auto_dispatch_commands(suggestions)
            return suggestions
        return actions

    # ------------------------------------------------------------------
    # Integration hooks
    # ------------------------------------------------------------------
    def support_functions(
        self,
        *,
        connector_registry: Any | None = None,
        persona_loader: Optional[Callable[[str], Dict[str, Any]]] = None,
        telemetry_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Callable[..., Any]]:
        """Expose helpers that wire the bridge into a connector ecosystem.

        Parameters
        ----------
        connector_registry:
            Object responsible for routing :class:`COMMAND` payloads. The
            object must expose either a ``dispatch`` or ``send`` method.
        persona_loader:
            Callable used to retrieve agent personas by identifier.
        telemetry_handler:
            Callable invoked with telemetry payloads emitted by strategies.
        """

        if connector_registry is not None:
            self._connector_registry = connector_registry
        if persona_loader is not None:
            self._persona_loader = persona_loader
        if telemetry_handler is not None:
            self._telemetry_handler = telemetry_handler

        def route_command(payload: Dict[str, Any]) -> Any:
            return self._execute_command(payload)

        def load_persona(persona_id: str) -> Dict[str, Any]:
            if self._persona_loader is None:
                raise RuntimeError("No persona loader configured")
            persona = self._persona_loader(persona_id)
            if persona is None:
                raise ValueError(f"Persona '{persona_id}' not found")
            self._active_persona = persona
            return persona

        def session_context(
            session_id: str, updates: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            session = self._session_store.get_session(session_id)
            if updates:
                self._session_store.update_metadata(session_id, updates)
            return session

        def emit_telemetry(event: Dict[str, Any]) -> Dict[str, Any]:
            self._emit_telemetry(event)
            return event

        return {
            "route_command": route_command,
            "load_persona": load_persona,
            "session_context": session_context,
            "emit_telemetry": emit_telemetry,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _emit_telemetry(self, payload: Dict[str, Any]) -> None:
        if self._telemetry_handler:
            self._telemetry_handler(payload)

    # ------------------------------------------------------------------
    # Command execution helpers
    # ------------------------------------------------------------------
    def _resolve_dispatcher(self) -> Callable[[str, Dict[str, Any]], Any]:
        if self._connector_registry is None:
            raise RuntimeError("No connector registry configured")
        dispatcher = getattr(self._connector_registry, "dispatch", None)
        if dispatcher is None:
            dispatcher = getattr(self._connector_registry, "send", None)
        if dispatcher is None:
            raise AttributeError(
                "Connector registry must implement `dispatch` or `send`"
            )
        return dispatcher

    def _execute_command(self, payload: Dict[str, Any]) -> Any:
        command = payload.get("command")
        if isinstance(command, COMMAND):
            command_value = command.value
        else:
            command_value = str(command)
        body = {k: v for k, v in payload.items() if k != "command"}
        dispatcher = self._resolve_dispatcher()
        result = dispatcher(command_value, body)
        self._emit_telemetry(
            {
                "type": "command_dispatch",
                "command": command_value,
                "payload": body,
                "session_id": self.goal_state.get("session_id"),
            }
        )
        return result

    def _auto_dispatch_commands(self, suggestions: List[Dict]) -> None:
        if not self._connector_registry:
            return
        auto_dispatch_enabled = self.goal_state.get("auto_dispatch", True)
        for suggestion in suggestions:
            for command in suggestion.get("commands", []) or []:
                auto_execute = command.get("auto_execute")
                if auto_execute or (auto_dispatch_enabled and auto_execute is not False):
                    try:
                        self._execute_command(command)
                    except Exception as exc:  # pragma: no cover - defensive
                        self._emit_telemetry(
                            {
                                "type": "command_dispatch_error",
                                "command": str(command.get("command")),
                                "error": str(exc),
                                "session_id": self.goal_state.get("session_id"),
                            }
                        )
