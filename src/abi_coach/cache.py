"""Backward compatibility shim for abi_coach.cache."""

from abi_coach.core.storage.cache import CacheEntry, MindCacheLRU

__all__ = ["CacheEntry", "MindCacheLRU"]
