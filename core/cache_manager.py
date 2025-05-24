from typing import Any, Optional
from datetime import datetime, timedelta


class CacheManager:
    """
    In-memory cache with optional TTL support.
    Supports get/set/invalidate/clear methods.
    """
    def __init__(self):
        self.cache = {}  # key -> (value, expiry)

    def get(self, key: str) -> Optional[Any]:
        entry = self.cache.get(key)
        if not entry:
            return None
        value, expiry = entry
        if expiry and expiry < datetime.utcnow():
            self.invalidate(key)
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set a cache entry.
        :param key: cache key
        :param value: value to store
        :param ttl: time-to-live in seconds (optional)
        """
        expiry = datetime.utcnow() + timedelta(seconds=ttl) if ttl else None
        self.cache[key] = (value, expiry)

    def invalidate(self, key: str):
        self.cache.pop(key, None)

    def clear(self):
        self.cache.clear()
