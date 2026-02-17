"""Adaptive routing policies based on lightweight multi-armed bandits."""

from __future__ import annotations

import os
import random
import re
import sqlite3
import threading
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .expert_registry import RegisteredExpert
from .policies import RoutingPolicy


_SQLITE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SQLITE_RESERVED_KEYWORDS = {
    "ABORT", "ACTION", "ADD", "AFTER", "ALL", "ALTER", "ANALYZE", "AND", "AS", "ASC",
    "ATTACH", "AUTOINCREMENT", "BEFORE", "BEGIN", "BETWEEN", "BY", "CASCADE", "CASE", "CAST", "CHECK",
    "COLLATE", "COLUMN", "COMMIT", "CONFLICT", "CONSTRAINT", "CREATE", "CROSS", "CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP",
    "DATABASE", "DEFAULT", "DEFERRABLE", "DEFERRED", "DELETE", "DESC", "DETACH", "DISTINCT", "DROP", "EACH",
    "ELSE", "END", "ESCAPE", "EXCEPT", "EXCLUSIVE", "EXISTS", "EXPLAIN", "FAIL", "FILTER", "FOR",
    "FOREIGN", "FROM", "FULL", "GLOB", "GROUP", "HAVING", "IF", "IGNORE", "IMMEDIATE", "IN",
    "INDEX", "INDEXED", "INITIALLY", "INNER", "INSERT", "INSTEAD", "INTERSECT", "INTO", "IS", "ISNULL",
    "JOIN", "KEY", "LEFT", "LIKE", "LIMIT", "MATCH", "NATURAL", "NO", "NOT", "NOTNULL",
    "NULL", "OF", "OFFSET", "ON", "OR", "ORDER", "OUTER", "PLAN", "PRAGMA", "PRIMARY",
    "QUERY", "RAISE", "RECURSIVE", "REFERENCES", "REGEXP", "REINDEX", "RELEASE", "RENAME", "REPLACE", "RESTRICT",
    "RIGHT", "ROLLBACK", "ROW", "SAVEPOINT", "SELECT", "SET", "TABLE", "TEMP", "TEMPORARY", "THEN",
    "TO", "TRANSACTION", "TRIGGER", "UNION", "UNIQUE", "UPDATE", "USING", "VACUUM", "VALUES", "VIEW",
    "VIRTUAL", "WHEN", "WHERE", "WINDOW", "WITH", "WITHOUT",
}


def _is_valid_sqlite_identifier(identifier: str) -> bool:
    if not _SQLITE_IDENTIFIER_RE.fullmatch(identifier):
        return False
    return identifier.upper() not in _SQLITE_RESERVED_KEYWORDS


@dataclass
class _RewardStats:
    count: int = 0
    total_reward: float = 0.0

    @property
    def average_reward(self) -> float:
        if self.count <= 0:
            return 0.0
        return self.total_reward / self.count


class EpsilonGreedyRoutingPolicy(RoutingPolicy):
    """Route to experts using an epsilon-greedy reward policy."""

    def __init__(
        self,
        *,
        epsilon: float = 0.1,
        database: str = ":memory:",
        table_name: str = "bandit_routing_stats",
        random_seed: int | None = None,
    ) -> None:
        if not 0.0 <= epsilon <= 1.0:
            raise ValueError("epsilon must be between 0.0 and 1.0")
        if not _is_valid_sqlite_identifier(table_name):
            raise ValueError(
                "table_name must be a valid SQLite identifier (letters/digits/underscores, "
                "starting with a letter or underscore, and not a reserved keyword)"
            )

        self._epsilon = float(epsilon)
        self._database = database
        self._table_name = table_name
        self._rng = random.Random(random_seed)
        self._lock = threading.RLock()
        self._stats: dict[tuple[str, str], dict[str, _RewardStats]] = defaultdict(dict)

        if database != ":memory:":
            directory = os.path.dirname(os.path.abspath(database))
            if directory:
                os.makedirs(directory, exist_ok=True)
        self._connection = sqlite3.connect(self._database, check_same_thread=False)
        self._ensure_schema()
        self._load_all_stats()

    def select(
        self,
        experts: list[RegisteredExpert],
        request: dict[str, Any],
        goal_context: dict[str, Any],
        context_layers: list[str],
    ) -> list[str]:
        if not experts:
            return []

        filtered_experts = self._filter_by_capabilities(
            experts=experts,
            request=request,
            goal_context=goal_context,
            context_layers=context_layers,
        )
        if not filtered_experts:
            return []

        context_key = self._resolve_context_key(request, goal_context)
        available_ids = [expert.expert_id for expert in filtered_experts]

        with self._lock:
            if self._rng.random() < self._epsilon:
                return [self._rng.choice(available_ids)]

            stats_for_context = self._stats.get(context_key, {})
            best_expert_id = available_ids[0]
            best_score = stats_for_context.get(best_expert_id, _RewardStats()).average_reward
            for expert_id in available_ids[1:]:
                score = stats_for_context.get(expert_id, _RewardStats()).average_reward
                if score > best_score:
                    best_expert_id = expert_id
                    best_score = score
            return [best_expert_id]

    def _filter_by_capabilities(
        self,
        *,
        experts: list[RegisteredExpert],
        request: dict[str, Any],
        goal_context: dict[str, Any],
        context_layers: list[str],
    ) -> list[RegisteredExpert]:
        request_category = request.get("category") or goal_context.get("category")
        request_scope = request.get("scope") or goal_context.get("scope")
        request_tags = set(request.get("tags") or [])
        available_layers = set(context_layers)

        selected: list[RegisteredExpert] = []
        for entry in experts:
            capabilities = entry.capabilities

            category = capabilities.get("category")
            if category is not None and request_category is not None and category != request_category:
                continue

            scope = capabilities.get("scope")
            if scope is not None and request_scope is not None and scope != request_scope:
                continue

            tags = set(capabilities.get("tags") or [])
            if request_tags and not request_tags.issubset(tags):
                continue

            required_layers = set(capabilities.get("layers") or [])
            if required_layers and not required_layers.issubset(available_layers):
                continue

            selected.append(entry)

        return selected

    def record_outcome(
        self,
        expert_id: str,
        reward: float,
        context_meta: dict[str, Any] | None = None,
    ) -> None:
        """Record an expert reward outcome for the provided context metadata."""
        context_key = self._resolve_context_key(context_meta or {}, context_meta or {})

        with self._lock:
            stats = self._stats[context_key].get(expert_id)
            if stats is None:
                stats = _RewardStats()
                self._stats[context_key][expert_id] = stats
            stats.count += 1
            stats.total_reward += float(reward)
            self._persist(context_key=context_key, expert_id=expert_id, stats=stats)

    def _resolve_context_key(
        self,
        request: dict[str, Any],
        goal_context: dict[str, Any],
    ) -> tuple[str, str]:
        goal = (
            request.get("goal")
            or request.get("goal_id")
            or goal_context.get("goal")
            or goal_context.get("goal_id")
            or "__global__"
        )
        task = (
            request.get("task")
            or request.get("task_id")
            or goal_context.get("task")
            or goal_context.get("task_id")
            or "__default__"
        )
        return str(goal), str(task)

    def _ensure_schema(self) -> None:
        with self._lock:
            self._connection.execute(
                f"CREATE TABLE IF NOT EXISTS {self._table_name} ("
                "goal_key TEXT NOT NULL,"
                "task_key TEXT NOT NULL,"
                "expert_id TEXT NOT NULL,"
                "count INTEGER NOT NULL,"
                "total_reward REAL NOT NULL,"
                "PRIMARY KEY (goal_key, task_key, expert_id)"
                ")"
            )
            self._connection.commit()

    def _load_all_stats(self) -> None:
        with self._lock:
            rows = self._connection.execute(
                f"SELECT goal_key, task_key, expert_id, count, total_reward FROM {self._table_name}"
            ).fetchall()

            for goal_key, task_key, expert_id, count, total_reward in rows:
                self._stats[(str(goal_key), str(task_key))][str(expert_id)] = _RewardStats(
                    count=int(count),
                    total_reward=float(total_reward),
                )

    def _persist(self, *, context_key: tuple[str, str], expert_id: str, stats: _RewardStats) -> None:
        goal_key, task_key = context_key
        with self._lock:
            self._connection.execute(
                f"INSERT INTO {self._table_name} (goal_key, task_key, expert_id, count, total_reward) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(goal_key, task_key, expert_id) DO UPDATE SET "
                "count = excluded.count, total_reward = excluded.total_reward",
                (goal_key, task_key, expert_id, stats.count, stats.total_reward),
            )
            self._connection.commit()
