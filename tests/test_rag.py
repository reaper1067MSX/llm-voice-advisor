"""Unit tests for KnowledgeRAG tactical retrieval system."""

from pathlib import Path
import pytest

from abi_coach.db import DatabaseManager
from abi_coach.rag import KnowledgeItem, KnowledgeRAG


def test_knowledge_rag_seed_and_search(tmp_path: Path):
    db_file = tmp_path / "test_rag.sqlite3"
    db = DatabaseManager(str(db_file))
    rag = KnowledgeRAG(db, default_game="abi")

    # 1. Verify default seed was loaded
    m80 = rag.get_entity("ammo:7.62x51:m80")
    assert m80 is not None
    assert "7.62x51mm" in m80["data_json"]
    assert m80["game"] == "abi"

    # 2. Search exact bullet code
    results = rag.search("M80", game="abi")
    assert len(results) >= 1
    assert "M80" in results[0]["title"]
    assert results[0]["entity_key"] == "ammo:7.62x51:m80"

    # 3. Search multi-word term
    dumdum_res = rag.search("Dum-Dum", game="abi")
    assert len(dumdum_res) >= 1
    assert "Dum-Dum" in dumdum_res[0]["title"]

    # 4. Search zone / point of interest
    motel_res = rag.search("Motel", game="abi")
    assert len(motel_res) >= 1
    assert "Motel" in motel_res[0]["title"]


def test_knowledge_rag_upsert_and_prompt_formatting(tmp_path: Path):
    db_file = tmp_path / "test_rag_upsert.sqlite3"
    db = DatabaseManager(str(db_file))
    rag = KnowledgeRAG(db, default_game="abi")

    # Insert custom item
    custom_item = KnowledgeItem(
        game="abi",
        category="weapon",
        entity_key="weapon:fal:meta_build",
        title="FAL Meta S7",
        data_json='{"recoil_v": 58, "recoil_h": 46, "ergo": 55}',
        summary="Build recomendada: compensador de asalto, empuñadura táctica y culata PRS.",
        source="player_verified",
        game_version="S7.1",
        confidence=0.95,
    )
    row_id = rag.upsert_knowledge(custom_item)
    assert row_id is not None

    # Search custom item
    res = rag.search("FAL", game="abi")
    assert len(res) >= 1
    assert "FAL Meta S7" in res[0]["title"]

    # Format for prompt
    ctx = rag.format_context_for_prompt("¿Qué accesorios le pongo al FAL?", game="abi")
    assert "BASE DE DATOS TÁCTICA VERIFICADA" in ctx
    assert "FAL Meta S7" in ctx
    assert "compensador de asalto" in ctx


def test_brain_integrates_rag_facts(tmp_path: Path):
    from abi_coach.brain import Brain
    from abi_coach.config import AppConfig
    from abi_coach.providers.base import ProviderResponse

    captured_kwargs = {}

    class MockProvider:
        def generate(self, prompt, system_instruction, image_bytes=None, crop_bytes=None, history_text=None, tool_callback=None):
            captured_kwargs["prompt"] = prompt
            captured_kwargs["history_text"] = history_text
            return ProviderResponse(spoken_text="Usa M80 que tiene 44 de penetración.")

    db_file = tmp_path / "brain_rag.sqlite3"
    db = DatabaseManager(str(db_file))
    rag = KnowledgeRAG(db, default_game="abi")

    cfg = AppConfig()
    cfg.gemini.game = "abi"

    brain = Brain(config=cfg, provider=MockProvider(), rag=rag)
    res = brain.ask("¿Cuál es la penetración de la bala M80?")

    assert "Usa M80" in res.spoken_text
    assert captured_kwargs["prompt"] == "¿Cuál es la penetración de la bala M80?"
    # Verify RAG context was injected into history_text passed to provider
    history_text = captured_kwargs["history_text"]
    assert any("BASE DE DATOS TÁCTICA VERIFICADA" in line for line in history_text)
    assert any("Bala 7.62x51mm M80" in line for line in history_text)


def test_brain_fast_path_zero_llm(tmp_path: Path):
    from abi_coach.brain import Brain
    from abi_coach.config import AppConfig

    class UnreachableProvider:
        def generate(self, *args, **kwargs):
            raise AssertionError("LLM Provider should NOT be called for exact stat queries!")

    db_file = tmp_path / "brain_fastpath.sqlite3"
    db = DatabaseManager(str(db_file))
    rag = KnowledgeRAG(db, default_game="abi")

    cfg = AppConfig()
    cfg.gemini.game = "abi"

    brain = Brain(config=cfg, provider=UnreachableProvider(), rag=rag)
    res = brain.ask("¿Qué penetración tiene la bala M80?")

    assert res is not None
    assert "44 de penetración" in res.spoken_text
    assert "76 de daño base" in res.spoken_text
    assert res.input_tokens == 0
    assert len(brain.history) == 2
    assert brain.history[0].role == "user"
    assert brain.history[1].role == "coach"


def test_create_tactical_dashboard(tmp_path: Path):
    from abi_coach.reports import create_tactical_dashboard

    memories = [
        {"topic": "loadouts", "feature": "weapon", "title": "FAL Principal", "content": "Mira 1x/4x", "pinned": True}
    ]
    knowledge = [
        {"title": "Bala 7.62x51mm M80", "data_json": '{"tier": 4, "penetration": 44, "damage": 76}', "summary": "Balanceada"}
    ]

    out_dir = tmp_path / "reports"
    dashboard_path = create_tactical_dashboard(
        memory_items=memories,
        knowledge_items=knowledge,
        game="abi",
        output_dir=str(out_dir),
        auto_open=False,
    )

    assert dashboard_path.exists()
    content = dashboard_path.read_text(encoding="utf-8")
    assert "Dashboard Táctico - ABI" in content
    assert "FAL Principal" in content
    assert "Bala 7.62x51mm M80" in content
    assert "dashboardChart" in content
    assert "Content-Security-Policy" in content

