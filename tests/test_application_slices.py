"""Unit tests for Application Vertical Slices and Presentation driving adapters."""

from pathlib import Path
import pytest

from abi_coach.application.orchestration.brain import Brain
from abi_coach.application.pipeline import (
    ExceptionHandlingMiddleware,
    ExecutionPipeline,
    LoggingMiddleware,
)
from abi_coach.application.slices import (
    AskTacticalAdviceCommand,
    CompanionMemoryHandler,
    ContextSwitchHandler,
    GetActiveProfileQuery,
    MetaTuningHandler,
    ProcessMetaTuningCommand,
    ReconcileFactCommand,
    SaveMemoryCommand,
    SearchKnowledgeQuery,
    SwitchContextCommand,
    TacticalAdviceDTO,
    TacticalAdviceHandler,
    TacticalRagHandler,
)
from abi_coach.application.slices.companion_memory.memory import CompanionMemory
from abi_coach.application.slices.metatuning.engine import MetaTuningEngine
from abi_coach.application.slices.tactical_rag.rag import KnowledgeRAG
from abi_coach.application.slices.tactical_rag.reconciler import KnowledgeReconciler
from abi_coach.domain.common.value_objects import TopicKey
from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
from abi_coach.infrastructure.adapters.storage.sqlite_knowledge_repo import SqliteKnowledgeRepository
from abi_coach.infrastructure.adapters.storage.sqlite_manager import DatabaseManager
from abi_coach.infrastructure.adapters.storage.sqlite_memory_repo import SqliteMemoryRepository
from abi_coach.infrastructure.config.settings import AppConfig


@pytest.fixture
def mock_brain(tmp_path: Path) -> Brain:
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    class MockProvider:
        def generate(self, prompt, system_instruction, image_bytes=None, crop_bytes=None, history_text=None, tool_callback=None):
            return ProviderResponse(
                spoken_text="Mocked advice: M80 ammo is optimal.",
                input_tokens=100,
                output_tokens=25,
                latency_ms=85.0,
            )

    db = DatabaseManager(db_path=str(tmp_path / "app_slices.db"))
    return Brain(config=cfg, provider=MockProvider(), db=db)


def test_tactical_advice_slice_through_pipeline(mock_brain: Brain):
    handler = TacticalAdviceHandler(brain=mock_brain)
    pipeline = (
        ExecutionPipeline()
        .add_middleware(ExceptionHandlingMiddleware())
        .add_middleware(LoggingMiddleware())
    )

    cmd = AskTacticalAdviceCommand(prompt="¿Qué balas uso?")
    res = pipeline.execute(cmd, handler.handle)

    assert res.is_ok()
    dto: TacticalAdviceDTO = res.unwrap()
    assert dto.spoken_advice == "Mocked advice: M80 ammo is optimal."
    assert dto.tokens.total_tokens == 125
    assert dto.latency_ms > 0.0


def test_context_switching_slice(mock_brain: Brain):
    handler = ContextSwitchHandler(brain=mock_brain)
    cmd = SwitchContextCommand(context_id="tarkov", display_name="Escape from Tarkov")

    res = handler.handle(cmd)
    assert res.is_ok()
    ctx = res.unwrap()
    assert ctx.context_id == "tarkov"
    assert ctx.display_name == "Escape from Tarkov"
    assert ctx.is_active is True


def test_companion_memory_slice(mock_brain: Brain):
    repo = SqliteMemoryRepository(mock_brain.memory)
    handler = CompanionMemoryHandler(memory_port=repo)

    tk = TopicKey("abi/combat/stance")
    save_cmd = SaveMemoryCommand(
        topic_key=tk,
        title="Postura Táctica",
        content="Disparar agachado para menor dispersión",
        pinned=True,
    )
    save_res = handler.handle_save(save_cmd)
    assert save_res.is_ok()

    query = GetActiveProfileQuery(game="abi")
    prof_res = handler.handle_query_profile(query)
    assert prof_res.is_ok()
    profile = prof_res.unwrap()
    assert len(profile) == 1
    assert profile[0].title == "Postura Táctica"


def test_tactical_rag_slice(mock_brain: Brain):
    repo = SqliteKnowledgeRepository(mock_brain.rag, mock_brain.reconciler)
    handler = TacticalRagHandler(knowledge_port=repo)

    search_q = SearchKnowledgeQuery(query="M80", game="abi")
    search_res = handler.handle_search(search_q)
    assert search_res.is_ok()


def test_metatuning_slice(mock_brain: Brain):
    handler = MetaTuningHandler(engine=mock_brain.metatuning)
    cmd = ProcessMetaTuningCommand(prompt="A partir de ahora sé más agresivo con las extracciones")
    res = handler.handle(cmd)
    assert res.is_ok()
    directive = res.unwrap()
    assert directive is not None
    assert directive.action_taken == "rule_saved"
    assert "agresivo" in directive.spoken_feedback.lower() or "registrado" in directive.spoken_feedback.lower()
