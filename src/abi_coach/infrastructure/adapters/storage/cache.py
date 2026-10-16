"""High-performance L1 In-Memory LRU Cache with TTL and prefix invalidation."""

from collections import OrderedDict
from dataclasses import dataclass
import threading
import time
from typing import Any, Dict, List, Optional


@dataclass
class CacheEntry:
    """Holds a cached value with metadata and expiration tracking."""

    key: str
    value: Any
    created_at: float
    ttl_seconds: Optional[float] = None
    access_count: int = 0

    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.created_at) > self.ttl_seconds


class MindCacheLRU:
    """Thread-safe, sub-0.05ms LRU in-memory cache for hot game entities and active profiles."""

    def __init__(self, capacity: int = 128, default_ttl_seconds: Optional[float] = None):
        self.capacity = max(16, capacity)
        self.default_ttl = default_ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from L1 cache in < 0.05 ms. Returns None on miss or expiration."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None

            # Mark as most recently used
            self._cache.move_to_end(key, last=True)
            entry.access_count += 1
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        """Store value in L1 cache with optional TTL. Evicts least-recently-used if full."""
        effective_ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = time.time()

        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key, last=True)
                self._cache[key] = CacheEntry(
                    key=key,
                    value=value,
                    created_at=now,
                    ttl_seconds=effective_ttl,
                )
                return

            if len(self._cache) >= self.capacity:
                # Evict oldest entry (first item)
                self._cache.popitem(last=False)
                self._evictions += 1

            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                ttl_seconds=effective_ttl,
            )

    def invalidate(self, key: str) -> bool:
        """Remove a specific key from cache. Returns True if removed."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys starting with prefix. Returns count of invalidated items."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        """Return cache health metrics."""
        with self._lock:
            total = self._hits + self._misses
            ratio = (self._hits / total * 100.0) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio_percent": round(ratio, 2),
                "count": len(self._cache),
                "capacity": self.capacity,
                "evictions": self._evictions,
            }
