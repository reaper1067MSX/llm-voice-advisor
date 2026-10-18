"""Unit and integration tests for Architectural Audit Remediation fixes."""

from concurrent.futures import ThreadPoolExecutor
import inspect
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

import abi_coach
from abi_coach.application.orchestration.brain import Brain
from abi_coach.application.slices import (
    AskTacticalAdviceCommand,
    ContextSwitchHandler,
    MetaTuningHandler,
    ProcessMetaTuningCommand,
    SwitchContextCommand,
    TacticalAdviceHandler,
)
from abi_coach.application.slices.archetypes.manager import DynamicEntity
from abi_coach.application.slices.companion_memory.memory import MemoryItem
from abi_coach.application.slices.metatuning.engine import ClarificationState, MetaTuningEngine
from abi_coach.application.slices.reporting.reports import _bring_browser_to_front_worker
from abi_coach.domain.common.errors import ProviderError, SystemUnexpectedError
from abi_coach.domain.common.result import Failure, Success, fail
from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
from abi_coach.infrastructure.adapters.llm.gemini_adapter import GeminiAdapter
from abi_coach.infrastructure.adapters.llm.nvidia_adapter import NvidiaNimAdapter
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.adapters.vision import capture as capture_mod
from abi_coach.infrastructure.config.settings import AppConfig, CaptureConfig, GeminiConfig, NvidiaConfig
from abi_coach.presentation.cli.cli import check_api_keys


def test_bring_browser_to_front_worker_signature_accepts_3_args(monkeypatch):
    """Task 1.1: Verify _bring_browser_to_front_worker accepts (browser_type, title_query, focus_browser)."""
    sig = inspect.signature(_bring_browser_to_front_worker)
    params = list(sig.parameters.keys())
    assert params == ["browser_type", "title_query", "focus_browser"]
    assert sig.parameters["focus_browser"].default is False

    # Ensure calling with 3 positional arguments does not raise TypeError
    monkeypatch.setattr("abi_coach.application.slices.reporting.reports.os.name", "posix")
    _bring_browser_to_front_worker("firefox", "Dashboard", True)
    _bring_browser_to_front_worker("edge", "Reporte", False)


def test_split_brain_unification_memory_and_rag(tmp_path: Path):
    """Task 1.2: Verify v1/v2 memory and RAG are unified in Brain."""
    db = DatabaseManager(str(tmp_path / "split_brain.sqlite3"))
    cfg = AppConfig()
    cfg.gemini.game = "abi"
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    captured = {}

    class InspectingProvider:
        def generate(
            self,
            prompt,
            system_instruction,
            image_bytes=None,
            crop_bytes=None,
            history_text=None,
            tool_callback=None,
        ):
            captured["prompt"] = prompt
            captured["system_instruction"] = system_instruction
            captured["history_text"] = history_text or []
            return ProviderResponse(
                spoken_text="Consejo unificado.",
                input_tokens=40,
                output_tokens=15,
                latency_ms=25.0,
            )

    brain = Brain(config=cfg, db=db, provider=InspectingProvider())

    # 1. Save v1 CompanionMemory AND v2 Engram observation via MetaTuningEngine
    brain.memory.save_memory(
        MemoryItem(
            game="abi",
            topic="loadouts",
            feature="sniper",
            topic_key="abi/loadouts/sniper",
            memory_type="preference",
            title="Francotirador Favorito",
            content="Mosin Nagant con mira 3.5x",
            pinned=True,
        )
    )
    tuning_rule_res = brain.metatuning.process(
        "A partir de ahora prioriza siempre rutas silenciosas en Armería",
        context_id="abi",
    )
    assert tuning_rule_res is not None
    assert tuning_rule_res.action_taken == "rule_saved"

    sys_inst = brain.get_system_instruction()
    # Both v1 CompanionMemory and v2 Engram observations must be present
    assert "Francotirador Favorito" in sys_inst
    assert "Mosin Nagant con mira 3.5x" in sys_inst
    assert "rutas silenciosas en Armería" in sys_inst
    assert "[MEMORIA PERSISTENTE ENGRAM" in sys_inst

    # 2. Save a fact via MetaTuningEngine (v2 topic_entities) and verify Brain.ask() injects it
    ingest_res = brain.metatuning.process(
        "Registra que el rifle AEK971 tiene cadencia de 900 disparos por minuto",
        context_id="abi",
    )
    assert ingest_res is not None
    assert ingest_res.action_taken == "rag_ingested"

    brain.ask("¿Cómo funciona el rifle AEK971 en combate cercano?")
    joined_history = "\n".join(captured["history_text"])
    assert "ENTIDADES DINÁMICAS DEL CONTEXTO" in joined_history
    assert "AEK971" in joined_history
    assert "900 disparos por minuto" in joined_history

    # 3. Verify Brain.try_fast_path() checks v2 topic_entities when v1 rag has no match
    brain.archetype_mgr.upsert_entity(
        DynamicEntity(
            context_id="abi",
            category="ammo",
            entity_key="ammo:abi:7n39_igolnik",
            title="Bala 5.45x39mm 7N39 Igolnik",
            facets={"tier": 6, "penetration": 62, "damage": 39},
            summary="Bala perforante de tungsteno Tier 6.",
        )
    )
    fast_res = brain.try_fast_path("¿Qué penetración tiene la bala Igolnik?")
    assert fast_res is not None
    assert "62 de penetración" in fast_res.spoken_text
    assert "39 de daño base" in fast_res.spoken_text
    assert "Tier 6" in fast_res.spoken_text


def test_check_api_keys_nvidia_config_paths(monkeypatch):
    """Task 1.3: Verify check_api_keys checks config.nvidia.api_key, config.llm.nvidia.api_key, and env."""
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)

    cfg = AppConfig()
    cfg.llm.provider = "nvidia"
    cfg.nvidia.api_key = None
    assert check_api_keys(cfg) is False

    # Top-level config.nvidia.api_key
    cfg.nvidia.api_key = "nvapi-valid-key-123"
    assert check_api_keys(cfg) is True

    # Legacy nested config.llm.nvidia.api_key
    cfg.nvidia.api_key = None
    cfg.llm.nvidia = SimpleNamespace(api_key="nvapi-nested-key-456")
    assert check_api_keys(cfg) is True


def test_hexagonal_llm_adapters_tokens_tools_and_crops(monkeypatch):
    """Task 1.4: Verify GeminiAdapter and NvidiaNimAdapter handle token configs, tool calls, and crops."""
    # 1. GeminiAdapter with standard GeminiConfig (no max_output_tokens attribute on dataclass)
    fake_genai_client = MagicMock()
    fake_fc = SimpleNamespace(
        name="create_report_tool",
        args={"title": "Tabla Balística", "html_body": "<table></table>"},
    )
    fake_genai_response = SimpleNamespace(
        text="Aquí tienes el reporte táctico.",
        function_calls=[fake_fc],
        usage_metadata=SimpleNamespace(prompt_token_count=120, candidates_token_count=35),
    )
    fake_genai_client.models.generate_content.return_value = fake_genai_response
    monkeypatch.setattr(
        "abi_coach.infrastructure.adapters.llm.gemini_adapter.genai.Client",
        lambda api_key: fake_genai_client,
    )

    g_cfg = GeminiConfig()
    g_adapter = GeminiAdapter(config=g_cfg, api_key="fake-gemini-key")

    tool_calls = []

    def report_cb(title: str, html_body: str) -> str:
        tool_calls.append((title, html_body))
        return "created.html"

    g_res = g_adapter.generate(
        prompt="Compara M80 vs M62",
        system_instruction="Eres ABI Coach",
        image_bytes=b"fake_full_jpg",
        crop_bytes={"ammo_box": b"fake_crop_jpg"},
        history_text=["USER: hola"],
        tool_callback=report_cb,
    )
    assert g_res.is_ok()
    g_dto = g_res.unwrap()
    assert g_dto.spoken_text == "Aquí tienes el reporte táctico."
    assert g_dto.report_title == "Tabla Balística"
    assert g_dto.tokens.total_tokens == 155
    assert tool_calls == [("Tabla Balística", "<table></table>")]

    # 2. NvidiaNimAdapter with standard NvidiaConfig (uses max_tokens=500, no max_output_tokens)
    n_cfg = NvidiaConfig(max_tokens=450)
    n_adapter = NvidiaNimAdapter(config=n_cfg, api_key="fake-nvidia-key")

    fake_openai_client = MagicMock()
    fake_openai_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Respuesta desde NVIDIA NIM."))],
        usage=SimpleNamespace(prompt_tokens=80, completion_tokens=20),
    )
    fake_openai_client.chat.completions.create.return_value = fake_openai_response
    n_adapter.client = fake_openai_client

    n_res = n_adapter.generate(
        prompt="Analiza este inventario",
        system_instruction="Eres Game Advisor",
        image_bytes=b"fake_img",
        crop_bytes={"hud": b"fake_crop"},
        history_text=["USER: test"],
    )
    assert n_res.is_ok()
    n_dto = n_res.unwrap()
    assert n_dto.spoken_text == "Respuesta desde NVIDIA NIM."
    assert n_dto.tokens.total_tokens == 100
    call_kwargs = fake_openai_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 450
    # Verify both full image and crop image were encoded in user message content
    user_msg_content = call_kwargs["messages"][-1]["content"]
    image_items = [item for item in user_msg_content if item.get("type") == "image_url"]
    assert len(image_items) == 2


def test_metatuning_clarification_cancellation_and_ttl(tmp_path: Path):
    """Task 1.5: Verify ClarificationState cancellation phrases and 60s TTL expiration."""
    db = DatabaseManager(str(tmp_path / "metatuning_ttl.sqlite3"))
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    brain = Brain(config=cfg, db=db, provider=MagicMock())
    engine: MetaTuningEngine = brain.metatuning

    # 1. Trigger clarification state
    res1 = engine.process("Haz que el coach sea más inteligente con el loot", context_id="abi")
    assert res1 is not None
    assert res1.is_clarification is True
    assert isinstance(engine.pending_clarification, ClarificationState)

    # 2. Cancel via cancellation phrase
    cancel_res = engine.process("Cancela", context_id="abi")
    assert cancel_res is not None
    assert cancel_res.handled is True
    assert cancel_res.spoken_response == "Entendido, cancelé la configuración pendiente."
    assert engine.pending_clarification is None

    # 3. Trigger clarification again and test 60s TTL expiration
    res2 = engine.process("Haz que el coach sea más inteligente", context_id="abi")
    assert res2 is not None
    assert engine.pending_clarification is not None
    engine.pending_clarification.created_at = time.time() - 65.0

    # Normal gameplay question after TTL expiry should expire pending_clarification and return None
    res_after_ttl = engine.process("¿Qué penetración tiene la M80?", context_id="abi")
    assert res_after_ttl is None
    assert engine.pending_clarification is None


def test_brain_ask_result_and_application_slices_pipeline(tmp_path: Path):
    """Task 2.1: Verify Brain.ask_result() and slice handlers execute through ExecutionPipeline."""
    db = DatabaseManager(str(tmp_path / "pipeline_slices.sqlite3"))
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    class HealthyProvider:
        def generate(self, *args, **kwargs):
            return ProviderResponse(
                spoken_text="Respuesta saludable del pipeline.",
                input_tokens=50,
                output_tokens=20,
                latency_ms=30.0,
            )

    brain = Brain(config=cfg, db=db, provider=HealthyProvider())

    # 1. Brain.ask_result() Success
    ok_res = brain.ask_result("¿Cuál es la mejor ruta en Granja?")
    assert isinstance(ok_res, Success)
    assert ok_res.unwrap().spoken_text == "Respuesta saludable del pipeline."

    # 2. Brain.ask_result() Failure when provider raises unexpected exception
    class CrashingProvider:
        def generate(self, *args, **kwargs):
            raise RuntimeError("Fallo simulado de red")

    brain.provider = CrashingProvider()
    err_res = brain.ask_result("¿Cuál es la mejor ruta en Granja?")
    assert isinstance(err_res, Failure)
    assert isinstance(err_res.error, SystemUnexpectedError)
    assert "fallo temporal" in err_res.error.get_spoken_message().lower()

    # 3. Brain.ask_result() Failure when hexagonal adapter returns Failure(ProviderError)
    class FailingHexProvider:
        def generate(self, *args, **kwargs):
            return fail(
                ProviderError(
                    code="GEMINI_TIMEOUT",
                    message="Timeout en Gemini",
                    provider_name="gemini",
                    spoken_fallback="Mi conexión con Gemini tardó demasiado.",
                )
            )

    brain.provider = FailingHexProvider()
    hex_err_res = brain.ask_result("¿Cuál es la mejor ruta en Granja?")
    assert hex_err_res.is_err()
    assert hex_err_res.error.get_spoken_message() == "Mi conexión con Gemini tardó demasiado."

    # 4. Application Slice Handlers trap unexpected exceptions via built-in ExecutionPipeline
    advice_handler = TacticalAdviceHandler(brain=brain)
    slice_res = advice_handler.handle(AskTacticalAdviceCommand(prompt="¿Cómo avanzo?"))
    assert slice_res.is_err()
    assert slice_res.error.get_spoken_message()

    ctx_handler = ContextSwitchHandler(brain=brain)
    ctx_res = ctx_handler.handle(SwitchContextCommand(context_id="abi", display_name="ABI"))
    assert ctx_res.is_ok()

    mt_handler = MetaTuningHandler(engine=brain.metatuning)
    mt_res = mt_handler.handle(
        ProcessMetaTuningCommand(prompt="A partir de ahora sé breve", context_id="abi")
    )
    assert mt_res.is_ok()


def test_lazy_root_imports_pep562():
    """Task 2.2: Verify abi_coach lazy __getattr__ resolves all exports without eager hardware loading."""
    # Check in a clean subprocess that importing abi_coach.domain does not import faster_whisper or edge_tts
    code = (
        "import sys; import abi_coach.domain; "
        "assert 'faster_whisper' not in sys.modules; "
        "assert 'edge_tts' not in sys.modules; "
        "import abi_coach; "
        "assert abi_coach.Result is abi_coach.domain.Result"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Subprocess failed: {proc.stderr}"

    # Verify all symbols in __all__ resolve via abi_coach.<Symbol>
    for sym in abi_coach.__all__:
        val = getattr(abi_coach, sym)
        assert val is not None

    with pytest.raises(AttributeError):
        _ = abi_coach.NonExistentAttributeXYZ


def test_persistent_capture_executor():
    """Task 3.1: Verify capture module uses a persistent module-level ThreadPoolExecutor."""
    assert hasattr(capture_mod, "_CAPTURE_EXECUTOR")
    assert isinstance(capture_mod._CAPTURE_EXECUTOR, ThreadPoolExecutor)


def test_clean_root_directory_structure():
    """Task 4.1: Verify src/abi_coach/ top-level contains ONLY the 4 Clean Architecture layers + __init__.py & __main__.py."""
    pkg_root = Path(abi_coach.__file__).resolve().parent
    entries = {p.name for p in pkg_root.iterdir() if p.name != "__pycache__"}
    expected = {
        "application",
        "domain",
        "infrastructure",
        "presentation",
        "__init__.py",
        "__main__.py",
    }
    assert entries == expected, f"Unexpected entries in src/abi_coach/: {entries ^ expected}"


def test_v021_version_info_and_smartscreen_release_helpers(tmp_path: Path):
    """Verify v0.2.3 version bump, PE VSVersionInfo file, PyInstaller spec wiring, and SmartScreen batch helpers."""
    import importlib.util

    project_root = Path(abi_coach.__file__).resolve().parent.parent.parent
    assert abi_coach.__version__ == "0.2.3"

    pyproject_text = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.2.3"' in pyproject_text

    version_info_path = project_root / "version_info.txt"
    assert version_info_path.is_file()
    v_text = version_info_path.read_text(encoding="utf-8")
    assert "VSVersionInfo(" in v_text
    assert "StringStruct('CompanyName', 'Santiago Arguello')" in v_text
    assert "StringStruct('ProductName', 'LLM Game Advisor')" in v_text
    assert "StringStruct('FileVersion', '0.2.3.0')" in v_text
    assert "filevers=(0, 2, 3, 0)" in v_text

    spec_text = (project_root / "game_advisor.spec").read_text(encoding="utf-8")
    assert "version_info.txt" in spec_text

    build_script_path = project_root / "scripts" / "build_release.py"
    spec = importlib.util.spec_from_file_location("build_release", build_script_path)
    assert spec and spec.loader
    build_release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_release)

    build_release.create_smartscreen_helpers(tmp_path)
    launcher_bat = tmp_path / "Iniciar_Game_Advisor.bat"
    unblock_bat = tmp_path / "Desbloquear_SmartScreen.bat"
    assert launcher_bat.is_file()
    assert unblock_bat.is_file()
    assert "Unblock-File" in launcher_bat.read_text(encoding="utf-8")
    assert "TrustedPublisher" in unblock_bat.read_text(encoding="utf-8")


def test_kaspersky_pdm_exploit_heuristics_eliminated():
    """Verify that suspicious Win32 APIs triggering PDM:Exploit heuristics are eliminated from src/."""
    project_root = Path(abi_coach.__file__).resolve().parent.parent.parent
    src_dir = project_root / "src" / "abi_coach"

    forbidden_patterns = [
        "OpenInputDesktop",
        "WScript.Shell",
        "keybd_event",
        "OpenProcess",
        "SwitchToThisWindow",
        r"WinSta0\Default",
    ]

    violations = []
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for pattern in forbidden_patterns:
            if pattern in content:
                violations.append(f"{py_file.relative_to(project_root)}: contains '{pattern}'")

    assert not violations, f"Detected suspicious Win32 APIs in production code: {violations}"


def test_tactical_fsm_silence_and_resume_interception():
    """Verify TacticalFSM voice command interception for silence and resume."""
    from abi_coach.application.orchestration.fsm import TacticalFSM
    from abi_coach.domain.entities.tactical_state import TacticalState

    fsm = TacticalFSM(initial_state=TacticalState.EXPLORING)
    assert fsm.can_suggest_proactively() is True

    # Test silence commands
    res = fsm.intercept_voice_command("Silencio de radio")
    assert res == "Copiado, silencio de radio activo. Concentración total."
    assert fsm.state == TacticalState.RADIO_SILENCE
    assert fsm.can_suggest_proactively() is False

    # Test accent and normalization
    res2 = fsm.intercept_voice_command("¡Modo concentración!")
    assert res2 == "Copiado, silencio de radio activo. Concentración total."
    assert fsm.state == TacticalState.RADIO_SILENCE

    # Test resume commands
    res3 = fsm.intercept_voice_command("Reanuda")
    assert res3 == "Entendido, canal abierto. Te cubro las espaldas."
    assert fsm.state == TacticalState.EXPLORING
    assert fsm.can_suggest_proactively() is True

    # Test normal query is not intercepted
    assert fsm.intercept_voice_command("¿Qué munición recomiendas?") is None


def test_in_memory_blackboard_operations():
    """Verify thread-safe InMemoryBlackboard operations and state updates."""
    from abi_coach.domain.entities.tactical_state import TacticalState
    from abi_coach.infrastructure.adapters.storage.in_memory_blackboard import InMemoryBlackboard

    bb = InMemoryBlackboard()
    initial = bb.get_state()
    assert initial.game_id == "generic"
    assert initial.state == TacticalState.EXPLORING
    assert initial.danger_level == 0.0

    updated = bb.update_state(
        game_id="abi",
        state=TacticalState.COMBAT,
        screen_summary="Enemy squad spotted at North",
        danger_level=0.85,
        entities_in_view=["Player", "Enemy", "M4A1"],
    )
    assert updated.game_id == "abi"
    assert updated.state == TacticalState.COMBAT
    assert updated.danger_level == 0.85
    assert updated.is_in_combat() is True
    assert "Enemy" in updated.entities_in_view

    bb.set_tactical_state(TacticalState.RADIO_SILENCE)
    current = bb.get_state()
    assert current.state == TacticalState.RADIO_SILENCE
    assert current.is_silent() is True

    bb.reset()
    assert bb.get_state().state == TacticalState.EXPLORING


def test_brain_instant_silence_command_response(tmp_path: Path):
    """Verify Brain.ask intercepts silence commands instantly without calling LLM."""
    cfg = AppConfig()
    cfg.gemini.game = "abi"
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    mock_provider = MagicMock()
    brain = Brain(config=cfg, provider=mock_provider)

    # Issue silence command
    resp = brain.ask("Silencio de radio")
    assert "silencio de radio activo" in resp.spoken_text.lower()
    assert brain.fsm.state.value == "silence"
    assert brain.blackboard.get_state().state.value == "silence"
    mock_provider.generate.assert_not_called()

    # Issue resume command
    resp2 = brain.ask("Reanudar")
    assert "canal abierto" in resp2.spoken_text.lower()
    assert brain.fsm.state.value == "exploring"
    mock_provider.generate.assert_not_called()


def test_reports_html_template_constrained_dimensions():
    """Verify HTML_TEMPLATE in reports.py has max-width and chart constraints."""
    from abi_coach.application.slices.reporting.reports import HTML_TEMPLATE

    assert "max-width: 960px;" in HTML_TEMPLATE
    assert "margin: 0 auto;" in HTML_TEMPLATE
    assert "max-height: 320px;" in HTML_TEMPLATE
    assert "max-width: 920px;" in HTML_TEMPLATE


def test_structured_logger_exception_tracking(tmp_path: Path):
    """Verify StructuredLogger writes structured JSONL exception records."""
    import json
    from abi_coach.infrastructure.adapters.logging.structured_logger import StructuredLogger

    logger = StructuredLogger(logs_dir=tmp_path)
    log_file = tmp_path / "exceptions.jsonl"

    try:
        raise KeyError("create_report_report")
    except KeyError as exc:
        logger.log_exception(
            component="test_component",
            agent="BrainMaster",
            action="generate_content",
            exc=exc,
            prompt="test query",
        )

    assert log_file.is_file()
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["component"] == "test_component"
    assert record["agent"] == "BrainMaster"
    assert record["action"] == "generate_content"
    assert record["exception"]["type"] == "KeyError"
    assert "create_report_report" in record["exception"]["message"]
    assert record["extra"]["prompt"] == "test query"




