from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Optional


class CacheManager:
    """
    In-memory cache with optional TTL support.
    Supports get/set/invalidate/clear methods.
    """
    def __init__(self, max_entries: Optional[int] = None):
        self.cache: "OrderedDict[str, tuple[Any, Optional[datetime]]]" = OrderedDict()
        self.max_entries = max_entries

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
        self.cache.move_to_end(key)
        self.prune()

    def prune(self):
        """Remove expired entries and enforce max size limits."""
        self.prune_expired()
        if self.max_entries is None or self.max_entries <= 0:
            return
        while len(self.cache) > self.max_entries:
            self.cache.popitem(last=False)

    def prune_expired(self):
        """Drop entries past their expiry timestamp."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, (_, expiry) in self.cache.items()
            if expiry and expiry < now
        ]
        for key in expired_keys:
            self.cache.pop(key, None)

    def invalidate(self, key: str):
        self.cache.pop(key, None)

    def clear(self):
        self.cache.clear()
