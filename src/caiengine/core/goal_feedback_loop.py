from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple

import json
import sqlite3

try:
    import redis as _redis
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    _redis = None

try:
    from redis import Redis  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Redis = None  # type: ignore[misc,assignment]

from caiengine.interfaces.goal_feedback_strategy import GoalFeedbackStrategy


@dataclass
class GoalMetric:
    """Snapshot describing how a single metric is tracking against a goal."""

    goal: float
    current: float
    gap: float
    baseline: Optional[float]
    trend: str
    progress_ratio: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "current": self.current,
            "gap": self.gap,
            "baseline": self.baseline,
            "trend": self.trend,
            "progress_ratio": self.progress_ratio,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "GoalMetric":
        return cls(
            goal=float(payload["goal"]),
            current=float(payload["current"]),
            gap=float(payload["gap"]),
            baseline=payload.get("baseline"),
            trend=str(payload["trend"]),
            progress_ratio=payload.get("progress_ratio"),
        )


class GoalFeedbackPersistence(Protocol):
    """Persistence backend for goal feedback loop state."""

    def load_state(
        self,
    ) -> Tuple[
        List[Dict[str, Any]],
        Dict[str, float],
        Dict[str, Dict[str, Any]],
    ]:
        """Return previously stored history, baselines, and analytics."""

    def save_state(
        self,
        history: Iterable[Dict[str, Any]],
        baselines: Dict[str, float],
        last_analysis: Dict[str, Dict[str, Any]],
    ) -> None:
        """Persist the provided history, baselines, and analytics."""


class InMemoryGoalFeedbackPersistence:
    """Store goal feedback loop state inside the current process."""

    def __init__(self) -> None:
        self._history: List[Dict[str, Any]] = []
        self._baselines: Dict[str, float] = {}
        self._analysis: Dict[str, Dict[str, Any]] = {}

    def load_state(
        self,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float], Dict[str, Dict[str, Any]]]:
        return (
            [dict(item) for item in self._history],
            dict(self._baselines),
            {key: dict(value) for key, value in self._analysis.items()},
        )

    def save_state(
        self,
        history: Iterable[Dict[str, Any]],
        baselines: Dict[str, float],
        last_analysis: Dict[str, Dict[str, Any]],
    ) -> None:
        self._history = [dict(item) for item in history]
        self._baselines = dict(baselines)
        self._analysis = {key: dict(value) for key, value in last_analysis.items()}


class SQLiteGoalFeedbackPersistence:
    """Persist goal feedback loop state inside a SQLite database file."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payload TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS baselines (
                    metric TEXT PRIMARY KEY,
                    value REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    payload TEXT NOT NULL
                )
                """
            )

    def load_state(
        self,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float], Dict[str, Dict[str, Any]]]:
        history: List[Dict[str, Any]] = []
        baselines: Dict[str, float] = {}
        analysis: Dict[str, Dict[str, Any]] = {}
        with self._connect() as conn:
            cursor = conn.execute("SELECT payload FROM history ORDER BY id ASC")
            history = [json.loads(row[0]) for row in cursor]
            cursor = conn.execute("SELECT metric, value FROM baselines")
            baselines = {str(row[0]): float(row[1]) for row in cursor}
            cursor = conn.execute("SELECT payload FROM analysis WHERE id = 1")
            row = cursor.fetchone()
            if row:
                analysis = json.loads(row[0])
        return history, baselines, analysis

    def save_state(
        self,
        history: Iterable[Dict[str, Any]],
        baselines: Dict[str, float],
        last_analysis: Dict[str, Dict[str, Any]],
    ) -> None:
        serialised_history = [json.dumps(item) for item in history]
        with self._connect() as conn:
            conn.execute("DELETE FROM history")
            conn.execute("DELETE FROM baselines")
            conn.execute("DELETE FROM analysis")
            if serialised_history:
                conn.executemany(
                    "INSERT INTO history (payload) VALUES (?)",
                    [(payload,) for payload in serialised_history],
                )
            if baselines:
                conn.executemany(
                    "INSERT INTO baselines (metric, value) VALUES (?, ?)",
                    [(metric, float(value)) for metric, value in baselines.items()],
                )
            if last_analysis:
                conn.execute(
                    "INSERT INTO analysis (id, payload) VALUES (1, ?)",
                    (json.dumps(last_analysis),),
                )


class RedisGoalFeedbackPersistence:
    """Persist goal feedback loop state inside Redis."""

    def __init__(
        self,
        *,
        client: "Redis" | None = None,
        url: str | None = None,
        key_prefix: str = "goal_feedback",
    ) -> None:
        if client is None:
            if url is None:
                raise ValueError(
                    "RedisGoalFeedbackPersistence requires a client or connection URL"
                )
            if _redis is None:  # pragma: no cover - optional dependency enforcement
                raise ImportError(
                    "Redis support requires the 'redis' extra: pip install caiengine[redis]"
                )
            client = _redis.Redis.from_url(url, decode_responses=True)
        self._client = client
        self._key_prefix = key_prefix

    def _key(self, suffix: str) -> str:
        return f"{self._key_prefix}:{suffix}"

    def _read_json(self, key: str, default: Any) -> Any:
        raw = self._client.get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    def load_state(
        self,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float], Dict[str, Dict[str, Any]]]:
        history = self._read_json(self._key("history"), [])
        baselines = self._read_json(self._key("baselines"), {})
        analysis = self._read_json(self._key("analysis"), {})
        return list(history), dict(baselines), dict(analysis)

    def save_state(
        self,
        history: Iterable[Dict[str, Any]],
        baselines: Dict[str, float],
        last_analysis: Dict[str, Dict[str, Any]],
    ) -> None:
        self._client.set(self._key("history"), json.dumps(list(history)))
        self._client.set(self._key("baselines"), json.dumps(dict(baselines)))
        self._client.set(self._key("analysis"), json.dumps(dict(last_analysis)))


def create_goal_feedback_persistence(
    config: Dict[str, Any] | None,
) -> GoalFeedbackPersistence | None:
    """Build a goal feedback persistence backend from configuration."""

    if not config:
        return None
    backend_type = str(config.get("type", "memory")).lower()
    if backend_type in {"memory", "in_memory", "in-memory"}:
        return InMemoryGoalFeedbackPersistence()
    if backend_type == "sqlite":
        path = config.get("path", "goal_feedback.db")
        return SQLiteGoalFeedbackPersistence(str(path))
    if backend_type == "redis":
        return RedisGoalFeedbackPersistence(
            client=config.get("client"),
            url=config.get("url"),
            key_prefix=config.get("key_prefix", "goal_feedback"),
        )
    raise ValueError(f"Unsupported goal feedback persistence type: {backend_type}")


class GoalDrivenFeedbackLoop:
    """Coordinate goal tracking, history management, and strategy suggestions."""

    def __init__(
        self,
        strategy: GoalFeedbackStrategy,
        goal_state: Dict | None = None,
        *,
        persistence: GoalFeedbackPersistence | None = None,
        retention_limit: Optional[int] = None,
        retention_window: Optional[timedelta | float | int] = None,
        timestamp_field: str = "timestamp",
    ):
        self.strategy = strategy
        self.goal_state = goal_state or {}
        self._persistence = persistence or InMemoryGoalFeedbackPersistence()
        self._timestamp_field = timestamp_field
        self._retention_limit = retention_limit if retention_limit is None else max(
            0, int(retention_limit)
        )
        if isinstance(retention_window, timedelta) or retention_window is None:
            self._retention_window = retention_window
        else:
            self._retention_window = timedelta(seconds=float(retention_window))
        self._history: List[Dict[str, Any]] = []
        self._baselines: Dict[str, float] = {}
        self._last_suggestions: List[Dict[str, Any]] = []
        self._last_analysis: Dict[str, GoalMetric] = {}
        self._load_persisted_state()

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return a shallow copy of the stored history."""

        return [dict(item) for item in self._history]

    @property
    def last_suggestions(self) -> List[Dict[str, Any]]:
        """Return the suggestions generated by the most recent call."""

        return [dict(item) for item in self._last_suggestions]

    @property
    def last_analysis(self) -> Dict[str, Dict[str, Any]]:
        """Return the most recent goal analytics in dictionary form."""

        return {metric: data.to_dict() for metric, data in self._last_analysis.items()}

    def reset_history(self) -> None:
        """Clear the stored history and baseline measurements."""

        self._history.clear()
        self._baselines.clear()
        self._last_analysis.clear()
        self._persist_state()

    def extend_history(self, entries: Iterable[Dict[str, Any]]) -> None:
        """Append entries to the stored history and update baselines."""

        changed = False
        for entry in entries:
            copied = dict(entry)
            self._attach_timestamp(copied)
            self._history.append(copied)
            self._register_baselines(copied)
            changed = True
        if not changed:
            return
        if self._enforce_retention():
            self._rebuild_baselines()
        self._persist_state()

    def set_goal_state(self, goal_state: Dict) -> None:
        """Update the desired context state."""

        self.goal_state = goal_state

    def suggest(self, history: List[Dict], current_actions: List[Dict]) -> List[Dict]:
        """Return actions nudging context toward :attr:`goal_state`.

        The loop keeps an internal copy of the most recent history so that
        callers do not need to resend the full timeline on every invocation.
        Suggestions are enriched with lightweight analytics describing the
        current gap to the goal and whether momentum is trending in the right
        direction.
        """

        combined_history = self._prepare_history(history)
        suggestions = self.strategy.suggest_actions(
            combined_history, current_actions, self.goal_state
        )
        analysis = self._analyse_history(combined_history)
        if analysis:
            analysis_payload = {key: metric.to_dict() for key, metric in analysis.items()}
            for suggestion in suggestions:
                suggestion.setdefault("goal_feedback", {})["analysis"] = analysis_payload
        self._last_suggestions = [dict(item) for item in suggestions]
        self._last_analysis = analysis
        self.extend_history(current_actions)
        return suggestions

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepare_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if history:
            self.reset_history()
            self.extend_history(history)
            return [dict(item) for item in history]
        return [dict(item) for item in self._history]

    def _load_persisted_state(self) -> None:
        history, baselines, analysis = self._persistence.load_state()
        if history:
            self._history = [dict(item) for item in history]
        if baselines:
            self._baselines = dict(baselines)
        if analysis:
            self._last_analysis = self._hydrate_analysis(analysis)
        if self._history and self._enforce_retention():
            self._rebuild_baselines()
            self._persist_state()

    def _persist_state(self) -> None:
        analysis_payload = {
            metric: data.to_dict() for metric, data in self._last_analysis.items()
        }
        self._persistence.save_state(self._history, self._baselines, analysis_payload)

    def _enforce_retention(self) -> bool:
        changed = False
        if self._retention_limit is not None and len(self._history) > self._retention_limit:
            self._history = self._history[-self._retention_limit :]
            changed = True
        if self._retention_window is not None:
            cutoff = self._now() - self._retention_window
            filtered: List[Dict[str, Any]] = []
            for entry in self._history:
                timestamp = self._entry_timestamp(entry)
                if timestamp is None or timestamp >= cutoff:
                    filtered.append(entry)
            if len(filtered) != len(self._history):
                self._history = filtered
                changed = True
        return changed

    def _rebuild_baselines(self) -> None:
        self._baselines.clear()
        for entry in self._history:
            self._register_baselines(entry)

    def _attach_timestamp(self, entry: Dict[str, Any]) -> None:
        if self._timestamp_field not in entry:
            entry[self._timestamp_field] = self._now().isoformat()

    def _entry_timestamp(self, entry: Dict[str, Any]) -> Optional[datetime]:
        raw = entry.get(self._timestamp_field)
        if raw is None:
            return None
        if isinstance(raw, datetime):
            return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
        if isinstance(raw, str):
            try:
                text = raw.strip()
            except AttributeError:
                return None
            if not text:
                return None
            try:
                if text.endswith("Z"):
                    text = text[:-1] + "+00:00"
                parsed = datetime.fromisoformat(text)
            except ValueError:
                return None
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return None

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _register_baselines(self, entry: Dict[str, Any]) -> None:
        for key, value in entry.items():
            numeric = self._coerce_numeric(value)
            if numeric is None or key in self._baselines:
                continue
            self._baselines[key] = numeric

    def _analyse_history(
        self, history: List[Dict[str, Any]]
    ) -> Dict[str, GoalMetric]:
        if not self.goal_state or not history:
            return {}

        last_state = history[-1]
        prev_state = history[-2] if len(history) > 1 else None
        analysis: Dict[str, GoalMetric] = {}

        for key, target in self.goal_state.items():
            if not isinstance(target, (int, float)):
                continue

            current_val = self._coerce_numeric(last_state.get(key))
            if current_val is None:
                continue

            previous_val = (
                self._coerce_numeric(prev_state.get(key)) if prev_state else None
            )
            baseline = self._baselines.get(key)
            gap = float(target) - current_val
            trend = self._determine_trend(current_val, previous_val, float(target))
            progress_ratio = self._progress_ratio(float(target), baseline, current_val)
            analysis[key] = GoalMetric(
                goal=float(target),
                current=current_val,
                gap=gap,
                baseline=baseline,
                trend=trend,
                progress_ratio=progress_ratio,
            )

        return analysis

    @staticmethod
    def _hydrate_analysis(
        payload: Dict[str, Dict[str, Any]]
    ) -> Dict[str, GoalMetric]:
        hydrated: Dict[str, GoalMetric] = {}
        for key, value in payload.items():
            if not isinstance(value, dict):
                continue
            try:
                hydrated[key] = GoalMetric.from_dict(value)
            except (KeyError, TypeError, ValueError):
                continue
        return hydrated

    @staticmethod
    def _coerce_numeric(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                stripped = value.strip()
            except AttributeError:
                return None
            if not stripped:
                return None
            try:
                return float(stripped)
            except ValueError:
                return None
        return None

    @staticmethod
    def _determine_trend(
        current: float, previous: Optional[float], target: float
    ) -> str:
        if previous is None:
            return "stable"
        delta = current - previous
        if delta == 0:
            return "stable"
        goal_direction = target - previous
        moved_toward_goal = (goal_direction >= 0 and delta > 0) or (
            goal_direction <= 0 and delta < 0
        )
        return "toward_goal" if moved_toward_goal else "away_from_goal"

    @staticmethod
    def _progress_ratio(
        target: float, baseline: Optional[float], current: float
    ) -> Optional[float]:
        if baseline is None:
            return None
        if target == baseline:
            return 1.0 if current == target else 0.0
        span = target - baseline
        if span == 0:
            return None
        if span > 0:
            ratio = (current - baseline) / span
        else:
            ratio = (baseline - current) / (baseline - target)
        return max(0.0, min(ratio, 1.0))
