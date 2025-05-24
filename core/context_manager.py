from core.cache_manager import CacheManager
from typing import Optional


class ContextManager:
    """
    Manages contextual memory with cache support.
    Supports roles, task state, history, embeddings, etc.
    """
    def __init__(self):
        self.cache = CacheManager()

    def _make_key(self, *parts) -> str:
        return ":".join(parts)

    def get_context(self, key: str) -> dict:
        return self.cache.get(key) or {}

    def get(self, key: str) -> dict:
        return self.get_context(key)

    def update_context(self, key: str, data: dict):
        current = self.get_context(key)
        current.update(data)
        self.cache.set(key, current)

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

    def clear_all(self):
        self.cache.clear()
