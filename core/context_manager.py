from core.cache_manager import CacheManager
class ContextManager:
    """
    Manages contextual memory with cache support.
    Stores past outputs, role assignments, states, etc. for history-aware reasoning.
    """
    def __init__(self):
        self.cache = CacheManager()
        # Additional storages can be added, e.g. persistent DB, etc.
        self.role_assignments = {}  # example: user_id -> role

    def get_context(self, key):
        """
        Retrieve stored context for the given key.
        """
        return self.cache.get(key) or {}

    def update_context(self, key, data: dict):
        """
        Update context data (merge with existing) for a key.
        """
        current = self.get_context(key)
        current.update(data)
        self.cache.set(key, current)

    def assign_role(self, user_id, role):
        """
        Track role assignment for a user.
        """
        self.role_assignments[user_id] = role

    def get_role(self, user_id):
        """
        Get role assigned to a user.
        """
        return self.role_assignments.get(user_id)

    def clear_context(self, key):
        self.cache.invalidate(key)

    def clear_all(self):
        self.cache.clear()
        self.role_assignments.clear()
