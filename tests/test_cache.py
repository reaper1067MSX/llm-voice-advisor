"""Unit tests for MindCacheLRU and L1 in-memory caching integration."""

from pathlib import Path
import time
import pytest

from abi_coach.application.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG
from abi_coach.infrastructure.adapters.storage.cache import MindCacheLRU
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager


def test_mind_cache_basic_lru_and_eviction():
    cache = MindCacheLRU(capacity=16)

    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    assert cache.get("c") is None

    # Test eviction: capacity is 16
    for i in range(16):
        cache.set(f"key_{i}", i)

    # First added keys should be evicted
    assert cache.get("a") is None
    assert cache.get("key_15") == 15
    assert cache.stats["count"] <= 16


def test_mind_cache_ttl_expiration():
    cache = MindCacheLRU(capacity=16, default_ttl_seconds=0.05)

    cache.set("temp", "hello")
    assert cache.get("temp") == "hello"

    time.sleep(0.06)
    assert cache.get("temp") is None
    assert cache.stats["misses"] >= 1


def test_mind_cache_invalidation_and_prefix():
    cache = MindCacheLRU(capacity=32)

    cache.set("game:abi:m80", {"pen": 44})
    cache.set("game:abi:m62", {"pen": 53})
    cache.set("game:once_human:mod1", {"tier": 5})

    assert cache.get("game:abi:m80") == {"pen": 44}

    # Invalidate single key
    removed = cache.invalidate("game:abi:m80")
    assert removed is True
    assert cache.get("game:abi:m80") is None

    # Invalidate prefix
    count = cache.invalidate_prefix("game:once_human:")
    assert count == 1
    assert cache.get("game:once_human:mod1") is None
    assert cache.get("game:abi:m62") is not None


def test_mind_cache_rag_integration(tmp_path: Path):
    db_file = tmp_path / "cache_rag.sqlite3"
    db = DatabaseManager(str(db_file))
    cache = MindCacheLRU(capacity=32)
    rag = KnowledgeRAG(db, default_game="abi", cache=cache)

    # 1. First get_entity: Cache miss, loads from SQLite
    m80 = rag.get_entity("ammo:7.62x51:m80")
    assert m80 is not None
    assert cache.stats["hits"] == 0
    assert cache.stats["misses"] == 1

    # 2. Second get_entity: Cache HIT in < 0.05ms!
    m80_cached = rag.get_entity("ammo:7.62x51:m80")
    assert m80_cached is not None
    assert cache.stats["hits"] == 1

    # 3. Search caching
    res1 = rag.search("M80", game="abi")
    assert len(res1) >= 1
    res2 = rag.search("M80", game="abi")
    assert len(res2) >= 1
    assert cache.stats["hits"] >= 2

    # 4. Invalidation on upsert
    rag.upsert_knowledge(
        KnowledgeItem(
            game="abi",
            category="ammo",
            entity_key="ammo:7.62x51:m80",
            title="M80 Buffeada",
            data_json='{"tier": 4, "penetration": 46, "damage": 78}',
            summary="Buffeada",
        )
    )
    # L1 cache must be invalidated
    assert cache.get("rag:entity:ammo:7.62x51:m80") is None
