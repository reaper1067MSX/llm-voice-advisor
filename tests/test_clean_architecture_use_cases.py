"""Unit tests for Clean Architecture Use Cases, Services, and Brain Thin Facade."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from abi_coach.application.orchestration.brain import (
    ABI_SYSTEM_INSTRUCTION,
    COACH_SYSTEM_INSTRUCTION,
    GENERIC_SYSTEM_INSTRUCTION,
    ONCE_HUMAN_SYSTEM_INSTRUCTION,
    Brain,
    CoachResponse,
    Turn,
    load_preset,
)
from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.application.services.prompt_registry import PromptTemplateRegistry
from abi_coach.application.services.report_coordinator import TacticalReportToolCoordinator
from abi_coach.application.slices.archetypes.manager import ArchetypeManager
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.slices.companion_memory.memory import CompanionMemory
from abi_coach.application.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG
from abi_coach.application.use_cases.context_switch import GameContextSwitchUseCase
from abi_coach.application.use_cases.fast_path_query import FastPathQueryUseCase
from abi_coach.application.use_cases.tactical_advice import TacticalAdviceUseCase
from abi_coach.domain.common.result import Success
from abi_coach.domain.entities.tactical_state import TacticalState
from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.config.settings import AppConfig


# ==========================================
# 1. Services Tests
# ==========================================

def test_prompt_template_registry_and_presets():
    """Verify PromptTemplateRegistry presets, fallback, and enrichment formatting."""
    registry = PromptTemplateRegistry()

    assert "Arena Breakout" in registry.get_preset("abi")
    assert "Once Human" in registry.get_preset("once_human")
    assert "Game Advisor" in registry.get_preset("generic")
    assert "Game Advisor" in registry.get_preset("unknown_custom_game")

    # Custom instruction overrides base preset
    custom = registry.build_system_instruction("abi", custom_instruction="Custom ABI Prompt")
    assert custom == "Custom ABI Prompt"

    # Memory and Archetype enrichments
    mock_memory = MagicMock()
    mock_memory.format_profile_for_prompt.return_value = "[PERFIL JUGADOR]: Francotirador"
    mock_archetype = MagicMock()
    mock_archetype.get_context.return_value = None
    mock_archetype.format_profile_for_prompt.return_value = "[REGLAS ENGRAM]: Usar suppressor"

    enriched = registry.build_system_instruction("abi", memory=mock_memory, archetype_mgr=mock_archetype)
    assert "[PERFIL JUGADOR]: Francotirador" in enriched
    assert "[REGLAS ENGRAM]: Usar suppressor" in enriched


def test_conversation_history_manager_window_and_threading():
    """Verify ConversationHistoryManager rolling window, slice bounds, truthiness, and concurrency."""
    mgr = ConversationHistoryManager(max_turns=4)

    # Truthiness when empty
    assert bool(mgr) is True
    assert len(mgr) == 0

    # Adding user-coach turns
    mgr.add_user_coach("Hola", "Saludos")
    assert len(mgr) == 2
    assert mgr[0].role == "user"
    assert mgr[1].role == "coach"

    # Slice bounds
    sl_zero = mgr.get_history_slice(0)
    assert sl_zero == []
    sl_one = mgr.get_history_slice(1)
    assert len(sl_one) == 2
    assert sl_one[0] == "USER: Hola"

    # Rolling window pruning
    for i in range(10):
        mgr.add_turn("user", f"msg {i}")
    assert len(mgr) == 4
    assert mgr[-1].text == "msg 9"

    # Clear
    mgr.clear()
    assert len(mgr) == 0

    # Thread-safe concurrent appends
    def worker(worker_id: int):
        for j in range(20):
            mgr.add_turn("user", f"w{worker_id}_{j}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(worker, range(4)))
    assert len(mgr) == 4  # Capped at max_turns=4


def test_tactical_report_tool_coordinator(tmp_path: Path):
    """Verify TacticalReportToolCoordinator report dispatch, callback generation, and dashboard."""
    rep_dir = str(tmp_path / "reports")
    opened_paths = []

    def mock_opener(path: str):
        opened_paths.append(path)

    coordinator = TacticalReportToolCoordinator(
        output_dir=rep_dir,
        auto_open=True,
        opener=mock_opener,
    )
    assert coordinator.last_report_path is None

    # create_report
    msg = coordinator.create_report("Test Report", "<table><tr><td>Stat</td></tr></table>")
    assert "exitosamente" in msg
    assert coordinator.last_report_path is not None
    assert Path(coordinator.last_report_path).is_file()

    # create_tool_callback
    cb = coordinator.create_tool_callback()
    res = cb("Tool Report", "<div>Data</div>")
    assert "exitosamente" in res

    # render_context_dashboard
    dash_path = coordinator.render_context_dashboard("abi", "Arena Breakout", "Tactical Shooter")
    assert dash_path is not None
    assert Path(dash_path).is_file()
    assert "Arena Breakout" in Path(dash_path).read_text(encoding="utf-8")


# ==========================================
# 2. Use Cases Tests
# ==========================================

def test_fast_path_query_use_case(tmp_path: Path):
    """Verify FastPathQueryUseCase deterministic numerical lookup and history recording."""
    db = DatabaseManager(str(tmp_path / "fastpath.db"))
    rag = KnowledgeRAG(db, default_game="abi")
    history_mgr = ConversationHistoryManager(50)
    use_case = FastPathQueryUseCase(rag=rag, history_mgr=history_mgr)

    # Non-stat query returns None
    assert use_case.execute("¿Cuál es la mejor táctica para jugar?") is None
    assert len(history_mgr) == 0

    # KnowledgeRAG already seeds M80 ammo in abi
    resp = use_case.execute("¿Qué penetración tiene la bala M80?", game_id="abi")
    assert resp is not None
    assert "44 de penetración" in resp.spoken_text
    assert "76 de daño base" in resp.spoken_text
    assert resp.input_tokens == 0
    assert len(history_mgr) == 2
    assert history_mgr[0].role == "user"
    assert history_mgr[1].role == "coach"


def test_game_context_switch_use_case(tmp_path: Path):
    """Verify GameContextSwitchUseCase verbal detection, execution, and state sync."""
    db = DatabaseManager(str(tmp_path / "ctx_switch.db"))
    archetype_mgr = ArchetypeManager(db)
    scaffolder = ArchetypeScaffolder(db, archetype_mgr)
    history_mgr = ConversationHistoryManager(50)
    cfg = AppConfig()

    use_case = GameContextSwitchUseCase(
        archetype_mgr=archetype_mgr,
        scaffolder=scaffolder,
        history_mgr=history_mgr,
        config=cfg,
    )

    # Verbal detection
    assert use_case.detect_request("Vamos a jugar Once Human") == ("once_human", "Once Human")
    assert use_case.detect_request("Cambia a modo advisor") == ("generic", "Game Advisor Universal")
    assert use_case.detect_request("Cambiemos a Cyberpunk 2077") == ("cyberpunk_2077", "Cyberpunk 2077")
    assert use_case.detect_request("¿Qué arma llevo?") is None

    # Execution
    ctx = use_case.execute("once_human", "Once Human")
    assert ctx.context_id == "once_human"
    assert cfg.gemini.game == "once_human"
    assert len(history_mgr) == 1
    assert "Contexto cambiado a Once Human" in history_mgr[0].text

    # Verbal switch handling
    resp = use_case.handle_verbal_switch("Vamos a darle a Arena Breakout")
    assert resp is not None
    assert "Arena Breakout" in resp.spoken_text
    assert cfg.gemini.game == "abi"


def test_tactical_advice_use_case_multimodal_and_fallbacks(tmp_path: Path):
    """Verify TacticalAdviceUseCase instant silence interception and LLM invocation."""
    history_mgr = ConversationHistoryManager(50)
    prompt_registry = PromptTemplateRegistry()
    report_coord = TacticalReportToolCoordinator(output_dir=str(tmp_path / "reports"), auto_open=False)

    class MockProvider:
        def __init__(self):
            self.calls = []

        def generate(self, prompt, system_instruction, image_bytes=None, crop_bytes=None, history_text=None, tool_callback=None):
            self.calls.append({"prompt": prompt, "history_text": history_text})
            return ProviderResponse(spoken_text="Mocked advice: Push with squadmate.", input_tokens=40, output_tokens=15, latency_ms=50.0)

    prov = MockProvider()
    use_case = TacticalAdviceUseCase(
        provider=prov,
        prompt_registry=prompt_registry,
        history_mgr=history_mgr,
        report_coordinator=report_coord,
    )

    resp = use_case.execute("¿Qué hacemos ahora?")
    assert resp.spoken_text == "Mocked advice: Push with squadmate."
    assert len(prov.calls) == 1
    assert len(history_mgr) == 2


# ==========================================
# 3. Brain Facade Tests
# ==========================================

def test_brain_facade_default_instantiation_and_delegation(tmp_path: Path):
    """Verify Brain thin facade instantiation, attributes, properties, and use case delegation."""
    cfg = AppConfig()
    cfg.gemini.api_key = "dummy-api-key"
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False
    db = DatabaseManager(str(tmp_path / "brain_facade.db"))

    class EchoProvider:
        def generate(self, prompt, system_instruction, **kwargs):
            return ProviderResponse(spoken_text=f"Echo: {prompt}", input_tokens=10, output_tokens=5, latency_ms=10.0)

    brain = Brain(config=cfg, db=db, provider=EchoProvider())

    # 1. Properties backward compatibility
    assert brain.current_game == "generic"
    brain.current_game = "abi"
    assert brain.active_context_id == "abi"
    assert isinstance(brain.history, list)
    assert brain._last_report_path is None

    # 2. Fast-path delegation
    brain.rag.upsert_knowledge(
        KnowledgeItem(
            game="abi",
            category="weapon",
            entity_key="weapon:mosin",
            title="Mosin Nagant",
            summary="Rifle de cerrojo",
            data_json='{"approx_value": 35000}',
        )
    )
    fp_res = brain.try_fast_path("¿Cuánto vale el Mosin?")
    assert fp_res is not None
    assert "35,000" in fp_res.spoken_text

    # 3. Context switch delegation
    ctx = brain.switch_context("once_human", "Once Human")
    assert ctx.context_id == "once_human"
    assert brain.current_game == "once_human"

    # 4. System instruction delegation
    sys_inst = brain.get_system_instruction()
    assert "Once Human" in sys_inst

    # 5. ask and ask_result delegation
    resp = brain.ask("Hola coach")
    assert resp.spoken_text == "Echo: Hola coach"

    result = brain.ask_result("Prueba de resultado")
    assert isinstance(result, Success)
    assert result.unwrap().spoken_text == "Echo: Prueba de resultado"

    # 6. Alias compatibility (screenshot parameter accepted)
    resp_img = brain.ask("Mira esto", screenshot=b"fake_png")
    assert "Echo: Mira esto" in resp_img.spoken_text
