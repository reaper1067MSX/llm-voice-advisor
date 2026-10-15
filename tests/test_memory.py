"""Unit tests for DatabaseManager and CompanionMemory persistence."""

from pathlib import Path
import pytest

from abi_coach.db import DatabaseManager
from abi_coach.memory import CompanionMemory, MemoryItem


def test_database_manager_wal_mode(tmp_path: Path):
    db_file = tmp_path / "test_advisor.sqlite3"
    db = DatabaseManager(str(db_file))
    con = db.get_connection()

    cur = con.cursor()
    cur.execute("PRAGMA journal_mode;")
    mode = cur.fetchone()[0]
    assert mode.lower() == "wal"


def test_companion_memory_crud_and_upsert(tmp_path: Path):
    db_file = tmp_path / "test_mem.sqlite3"
    db = DatabaseManager(str(db_file))
    mem = CompanionMemory(db, default_game="abi")

    # 1. Insert new memory
    item1 = MemoryItem(
        game="abi",
        topic="loadouts",
        feature="preferred_ammo",
        topic_key="abi/loadouts/preferred_ammo",
        memory_type="preference",
        title="Balas Favoritas",
        content="Prioriza M80 en 7.62x51mm y Dum-Dum en MP5.",
        pinned=True,
    )
    row_id = mem.save_memory(item1)
    assert row_id is not None

    # 2. Retrieve memory
    fetched = mem.get_memory("abi/loadouts/preferred_ammo")
    assert fetched is not None
    assert fetched["title"] == "Balas Favoritas"
    assert fetched["pinned"] == 1
    assert fetched["access_count"] >= 1

    # 3. Upsert update
    item1_updated = MemoryItem(
        game="abi",
        topic="loadouts",
        feature="preferred_ammo",
        topic_key="abi/loadouts/preferred_ammo",
        memory_type="preference",
        title="Balas Favoritas S7",
        content="M62 para Lockdown, M80 para normal.",
        pinned=True,
    )
    mem.save_memory(item1_updated)
    fetched2 = mem.get_memory("abi/loadouts/preferred_ammo")
    assert fetched2["title"] == "Balas Favoritas S7"
    assert fetched2["content"] == "M62 para Lockdown, M80 para normal."

    # 4. Search memory
    results = mem.search_memories("Lockdown", game="abi")
    assert len(results) == 1
    assert results[0]["topic_key"] == "abi/loadouts/preferred_ammo"

    # 5. Delete memory
    deleted = mem.delete_memory("abi/loadouts/preferred_ammo")
    assert deleted is True
    assert mem.get_memory("abi/loadouts/preferred_ammo") is None


def test_companion_memory_format_profile_for_prompt(tmp_path: Path):
    db_file = tmp_path / "test_prompt.sqlite3"
    db = DatabaseManager(str(db_file))
    mem = CompanionMemory(db, default_game="abi")

    mem.save_memory(
        MemoryItem(
            game="abi",
            topic="economy",
            feature="koen_balance",
            topic_key="abi/economy/koen_balance",
            memory_type="stat",
            title="Saldo de Koens",
            content="Aproximadamente 1.5M Koens en alijo.",
            pinned=False,
        )
    )
    mem.save_memory(
        MemoryItem(
            game="abi",
            topic="tactics",
            feature="hotspot_motel",
            topic_key="abi/tactics/hotspot_motel",
            memory_type="discovery",
            title="Cuidado en Motel",
            content="Evitar pasillo central sin granadas de humo.",
            pinned=True,
        )
    )

    formatted = mem.format_profile_for_prompt(game="abi")
    assert "[MEMORIA PERSISTENTE DEL JUGADOR" in formatted
    assert "Saldo de Koens" in formatted
    assert "Cuidado en Motel" in formatted
    assert "⭐ " in formatted  # pinned icon


def test_companion_memory_game_isolation(tmp_path: Path):
    db_file = tmp_path / "test_iso.sqlite3"
    db = DatabaseManager(str(db_file))
    mem = CompanionMemory(db)

    mem.save_memory(
        MemoryItem(
            game="abi",
            topic="rules",
            feature="rule1",
            topic_key="abi/rules/1",
            memory_type="rule",
            title="Regla ABI",
            content="La bala define el daño.",
        )
    )
    mem.save_memory(
        MemoryItem(
            game="generic",
            topic="rules",
            feature="rule1",
            topic_key="generic/rules/1",
            memory_type="rule",
            title="Regla Generic",
            content="Estrategia general.",
        )
    )

    abi_profile = mem.get_active_profile(game="abi")
    generic_profile = mem.get_active_profile(game="generic")

    assert len(abi_profile) == 1
    assert abi_profile[0]["title"] == "Regla ABI"
    assert len(generic_profile) == 1
    assert generic_profile[0]["title"] == "Regla Generic"


def test_brain_system_instruction_enriches_memory(tmp_path: Path):
    from abi_coach.brain import Brain
    from abi_coach.config import AppConfig
    from abi_coach.providers.base import ProviderResponse

    class DummyProvider:
        def generate(self, *args, **kwargs):
            return ProviderResponse(spoken_text="OK")

    db_file = tmp_path / "brain_mem.sqlite3"
    db = DatabaseManager(str(db_file))
    mem = CompanionMemory(db, default_game="abi")
    mem.save_memory(
        MemoryItem(
            game="abi",
            topic="loadouts",
            feature="weapon",
            topic_key="abi/loadouts/weapon",
            memory_type="preference",
            title="Arma Principal",
            content="FAL con M80 y mira 1x/4x.",
            pinned=True,
        )
    )

    cfg = AppConfig()
    cfg.gemini.game = "abi"

    brain = Brain(config=cfg, provider=DummyProvider(), memory=mem)
    instruction = brain.get_system_instruction()

    assert "FAL con M80" in instruction
    assert "[MEMORIA PERSISTENTE DEL JUGADOR" in instruction

