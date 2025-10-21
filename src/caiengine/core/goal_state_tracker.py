from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from copy import deepcopy
from typing import Any, Dict, Mapping, Protocol, TYPE_CHECKING

try:  # pragma: no cover - optional dependency resolution
    import redis as _redis
except ModuleNotFoundError:  # pragma: no cover - redis extra not installed
    _redis = None

if TYPE_CHECKING:  # pragma: no cover - import for type checking only
    from redis import Redis  # type: ignore


logger = logging.getLogger(__name__)


class GoalStateBackend(Protocol):
    """Protocol describing a persistence backend for goal state."""

    def load(self) -> Dict[str, Any]:
        """Return the current goal state."""

    def save(self, state: Dict[str, Any]) -> None:
        """Persist ``state``."""


class _InMemoryGoalStateBackend:
    """Fallback backend that keeps state in memory only."""

    def __init__(self) -> None:
        self._state: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._state)

    def save(self, state: Dict[str, Any]) -> None:
        with self._lock:
            self._state = deepcopy(state)


class SQLiteGoalStateBackend:
    """Persist goal state into a SQLite database.

    The state is stored as a single JSON blob inside the configured table,
    making the backend resilient to process restarts while remaining easy to
    inspect for debugging purposes.
    """

    def __init__(self, database: str, *, table_name: str = "goal_state") -> None:
        if not table_name.replace("_", "").isalnum():
            raise ValueError("table_name must be alphanumeric with optional underscores")
        self._database = database
        self._table_name = table_name
        self._lock = threading.RLock()
        if database != ":memory:":
            directory = os.path.dirname(os.path.abspath(database))
            if directory:
                os.makedirs(directory, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self._database, check_same_thread=False) as connection:
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table_name} ("
                "id INTEGER PRIMARY KEY CHECK (id = 1),"
                "payload TEXT NOT NULL"
                ")"
            )
            connection.execute(
                f"INSERT OR IGNORE INTO {self._table_name} (id, payload) VALUES (1, ?)",
                ("{}",),
            )
            connection.commit()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            with sqlite3.connect(self._database, check_same_thread=False) as connection:
                cursor = connection.execute(
                    f"SELECT payload FROM {self._table_name} WHERE id = 1"
                )
                row = cursor.fetchone()
        if not row:
            return {}
        serialized_state = row[0]
        try:
            return json.loads(serialized_state)
        except json.JSONDecodeError:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to decode goal state payload from SQLite; returning empty state",
                extra={"database": self._database, "table": self._table_name},
            )
            return {}

    def save(self, state: Dict[str, Any]) -> None:
        serialized_state = json.dumps(state, separators=(",", ":"))
        with self._lock:
            with sqlite3.connect(self._database, check_same_thread=False) as connection:
                connection.execute(
                    f"UPDATE {self._table_name} SET payload = ? WHERE id = 1",
                    (serialized_state,),
                )
                connection.commit()


class RedisGoalStateBackend:
    """Persist goal state using Redis as the storage backend."""

    def __init__(
        self,
        client: "Redis" | None = None,
        *,
        url: str | None = None,
        key: str = "caiengine:goal_state",
    ) -> None:
        if client is None:
            if url is None:
                raise ValueError("RedisGoalStateBackend requires a client or connection URL")
            if _redis is None:  # pragma: no cover - optional dependency enforcement
                raise ModuleNotFoundError(
                    "Redis support requires the 'redis' extra: pip install caiengine[redis]"
                )
            client = _redis.Redis.from_url(url)
        self._client = client
        self._key = key
        self._lock = threading.RLock()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            payload = self._client.get(self._key)
        if payload is None:
            return {}
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):  # pragma: no cover
            logger.error(
                "Failed to decode goal state payload from Redis; returning empty state",
                extra={"key": self._key},
            )
            return {}

    def save(self, state: Dict[str, Any]) -> None:
        serialized_state = json.dumps(state, separators=(",", ":"))
        with self._lock:
            self._client.set(self._key, serialized_state)


class GoalStateTracker:
    """Persist and retrieve goal feedback loop state.

    This is a placeholder for more robust storage such as a database or
    distributed cache.
    """

    def __init__(
        self,
        backend: GoalStateBackend | None = None,
        *,
        backend_config: Mapping[str, Any] | None = None,
    ) -> None:
        """Create a new tracker instance.

        Parameters
        ----------
        backend:
            A fully constructed :class:`GoalStateBackend` implementation. This is
            ideal when using dependency injection frameworks where the backend
            lifecycle is managed externally.
        backend_config:
            Declarative configuration describing how to build a backend. The
            supported configuration structure is::

                {"type": "sqlite", "database": "/tmp/goal_state.db"}
                {"type": "redis", "url": "redis://localhost/0", "key": "app:goal"}
                {"type": "memory"}

            Applications can load this mapping from settings files or
            environment-specific configuration and pass it directly to the
            tracker. Only one of ``backend`` or ``backend_config`` may be
            provided at a time.

        Example
        -------
        When wiring dependencies manually::

            backend_settings = settings["goal_state_backend"]
            tracker = GoalStateTracker(backend_config=backend_settings)

        """

        if backend and backend_config:
            raise ValueError("Provide either 'backend' or 'backend_config', not both")

        if backend is None and backend_config is not None:
            backend = self._build_backend_from_config(backend_config)

        resolved_backend: GoalStateBackend = backend or _InMemoryGoalStateBackend()
        self._backend = resolved_backend
        self._lock = threading.RLock()
        if (
            backend is None
            and backend_config is None
            and isinstance(resolved_backend, _InMemoryGoalStateBackend)
        ):
            logger.warning(
                "GoalStateTracker defaulting to in-memory storage; state will reset on restart",
                extra={"backend": "memory"},
            )

    def load(self) -> Dict[str, Any]:
        """Return the last known goal state and progress metrics."""
        with self._lock:
            state = self._backend.load()
        logger.debug(
            "Loaded goal state",
            extra={"keys": sorted(state.keys())},
        )
        return deepcopy(state)

    def save(self, state: Dict[str, Any]) -> None:
        """Persist updated goal state."""
        if not isinstance(state, dict):
            raise TypeError("Goal state must be a dictionary")
        snapshot = deepcopy(state)
        with self._lock:
            self._backend.save(snapshot)
        logger.info(
            "Persisted goal state",
            extra={"keys": sorted(snapshot.keys()), "size": len(snapshot)},
        )

    @staticmethod
    def _build_backend_from_config(config: Mapping[str, Any]) -> GoalStateBackend:
        if not config:
            raise ValueError("backend_config must not be empty")
        backend_type = str(config.get("type", "memory")).lower()
        if backend_type == "memory":
            return _InMemoryGoalStateBackend()
        if backend_type == "sqlite":
            database = config.get("database") or config.get("path")
            if not database:
                raise ValueError("SQLite backend requires 'database' or 'path'")
            table = config.get("table") or config.get("table_name", "goal_state")
            return SQLiteGoalStateBackend(str(database), table_name=str(table))
        if backend_type == "redis":
            key = str(config.get("key", "caiengine:goal_state"))
            client = config.get("client")
            if client is not None:
                if not hasattr(client, "get") or not hasattr(client, "set"):
                    raise TypeError("Redis client must provide 'get' and 'set' methods")
                return RedisGoalStateBackend(client=client, key=key)
            url = config.get("url")
            if url is None:
                raise ValueError("Redis backend requires a 'url' or 'client'")
            return RedisGoalStateBackend(url=str(url), key=key)
        raise ValueError(f"Unknown goal state backend type: {backend_type!r}")


__all__ = [
    "GoalStateBackend",
    "GoalStateTracker",
    "SQLiteGoalStateBackend",
    "RedisGoalStateBackend",
]
