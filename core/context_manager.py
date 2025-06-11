from core.cache_manager import CacheManager
from datetime import datetime
from typing import Optional, List


class ContextManager:
    """
    Manages contextual memory with cache support.
    Supports roles, task state, history, embeddings, etc.
    """
    def __init__(self):
        self.cache = CacheManager()
        self.history_cache = CacheManager()

    def _make_key(self, *parts) -> str:
        return ":".join(parts)

    def get_context(self, key: str) -> dict:
        return self.cache.get(key) or {}

    def get(self, key: str) -> dict:
        return self.get_context(key)

    def update_context(self, key: str, data: dict, ttl: Optional[int] = None, remember: bool = True):
        current = self.get_context(key)
        current.update(data)
        self.cache.set(key, current, ttl)
        if remember:
            hist_key = self._make_key("history", key, datetime.utcnow().isoformat())
            self.history_cache.set(hist_key, data, ttl)

    def assign_role(self, user_id: str, role: str):
        key = self._make_key("role", user_id)
        self.cache.set(key, role)

    def get_role(self, user_id: str) -> Optional[str]:
        key = self._make_key("role", user_id)
        return self.cache.get(key)

    def set_workflow_state(self, workflow_id: str, state: dict):
        key = self._make_key("workflow", workflow_id)
        self.cache.set(key, state)

    def get_workflow_state(self, workflow_id: str) -> dict:
        key = self._make_key("workflow", workflow_id)
        return self.get_context(key)

    def clear_context(self, key: str):
        self.cache.invalidate(key)

        prefix = self._make_key("history", key)
        for k in list(self.history_cache.cache.keys()):
            if k.startswith(prefix):
                self.history_cache.invalidate(k)

    def clear_all(self):
        self.cache.clear()
        self.history_cache.clear()

    def get_history(self, key: str) -> List[dict]:
        prefix = self._make_key("history", key)
        entries = []
        for k in list(self.history_cache.cache.keys()):
            if k.startswith(prefix):
                data = self.history_cache.get(k)
                if data is not None:
                    _, ts = k.rsplit(":", 1)
                    entries.append({"timestamp": ts, "data": data})
        return entries
