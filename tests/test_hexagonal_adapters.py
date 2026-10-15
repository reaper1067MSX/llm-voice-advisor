"""Unit tests for Hexagonal Infrastructure Adapters."""

from pathlib import Path
from PIL import Image
import pytest

from abi_coach.domain.common.value_objects import ConfidenceScore, TopicKey
from abi_coach.domain.entities.player_memory import PlayerMemory
from abi_coach.domain.entities.tactical_fact import TacticalFact
from abi_coach.infrastructure.adapters.reporting.browser_display_adapter import BrowserDisplayAdapter
from abi_coach.infrastructure.adapters.storage.sqlite_knowledge_repo import SqliteKnowledgeRepository
from abi_coach.infrastructure.adapters.storage.sqlite_manager import DatabaseManager
from abi_coach.infrastructure.adapters.storage.sqlite_memory_repo import SqliteMemoryRepository
from abi_coach.infrastructure.config.yaml_loader import AppConfig, CaptureConfig
from abi_coach.slices.companion_memory.memory import CompanionMemory
from abi_coach.slices.tactical_rag.rag import KnowledgeRAG
from abi_coach.slices.tactical_rag.reconciler import KnowledgeReconciler


@pytest.fixture
def test_db(tmp_path: Path) -> DatabaseManager:
    return DatabaseManager(db_path=str(tmp_path / "test_adapters.db"))


def test_sqlite_knowledge_repository_adapter(test_db: DatabaseManager):
    rag = KnowledgeRAG(test_db, default_game="abi")
    reconciler = KnowledgeReconciler(test_db, rag)
    repo = SqliteKnowledgeRepository(rag, reconciler)

    # 1. Save new TacticalFact
    fact = TacticalFact(
        game="abi",
        category="ammo",
        entity_key="762_m80",
        title="7.62x51mm M80",
        data_payload={"tier": 4, "penetration": 44, "damage": 75},
        summary="Bala militar estándar Tier 4.",
        confidence=ConfidenceScore(0.98),
    )
    save_res = repo.save(fact)
    assert save_res.is_ok()

    # 2. Get by key
    get_res = repo.get_by_key("762_m80", game="abi")
    assert get_res.is_ok()
    stored = get_res.unwrap()
    assert stored is not None
    assert stored.title == "7.62x51mm M80"
    assert stored.data_payload["penetration"] == 44

    # 3. Search
    search_res = repo.search("M80", game="abi")
    assert search_res.is_ok()
    items = search_res.unwrap()
    assert len(items) >= 1
    assert items[0].entity_key == "762_m80"

    # 4. Reconcile
    reconcile_res = repo.reconcile(
        entity_key="762_m80",
        observed_data={"tier": 4, "penetration": 45},  # diff by 1 point
        game="abi",
        reason="vision_reconcile",
    )
    assert reconcile_res.is_ok()
    diffs = reconcile_res.unwrap()
    assert len(diffs) == 1
    assert diffs[0].field_name == "penetration"
    assert diffs[0].new_value == 45


def test_sqlite_memory_repository_adapter(test_db: DatabaseManager):
    mem_core = CompanionMemory(test_db, default_game="abi")
    repo = SqliteMemoryRepository(mem_core)

    tk = TopicKey("abi/balistica/m80")
    mem = PlayerMemory(
        topic_key=tk,
        title="Regla M80",
        content="Priorizar siempre en raids caras",
        pinned=True,
    )

    # 1. Save memory
    save_res = repo.save_memory(mem)
    assert save_res.is_ok()

    # 2. Get memory
    get_res = repo.get_memory(tk)
    assert get_res.is_ok()
    retrieved = get_res.unwrap()
    assert retrieved is not None
    assert retrieved.title == "Regla M80"
    assert retrieved.pinned is True

    # 3. Get active profile
    prof_res = repo.get_active_profile(game="abi", limit=5)
    assert prof_res.is_ok()
    profile = prof_res.unwrap()
    assert len(profile) == 1
    assert profile[0].title == "Regla M80"


def test_browser_display_adapter(tmp_path: Path):
    cfg = AppConfig().reports
    cfg.output_dir = str(tmp_path / "reports")
    cfg.auto_open_browser = False

    adapter = BrowserDisplayAdapter(config=cfg)
    res = adapter.display_report(
        title="Reporte Adaptador",
        html_body="<div class='card'><h2>Contenido</h2></div>",
        auto_open=False,
    )
    assert res.is_ok()
    report_path = res.unwrap()
    assert report_path.is_file()
    assert "Reporte Adaptador" in report_path.read_text(encoding="utf-8")
