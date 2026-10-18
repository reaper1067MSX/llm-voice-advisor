"""Unit tests for hot context switching and Advisor onboarding configurator."""

from pathlib import Path
import pytest

from abi_coach.application.orchestration.advisor_orchestrator import AdvisorOrchestrator
from abi_coach.application.use_cases.context_switch_detector import ContextSwitchDetector
from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.config.settings import AppConfig


class DummyProvider:
    def __init__(self):
        self.last_system_instruction = None

    def generate(
        self,
        prompt,
        system_instruction,
        image_bytes=None,
        crop_bytes=None,
        history_text=None,
        tool_callback=None,
    ):
        self.last_system_instruction = system_instruction
        return ProviderResponse(spoken_text="Mocked response", input_tokens=10, output_tokens=10)


def test_detect_context_switch_request():
    detector = ContextSwitchDetector()

    # Extraction shooter
    req = detector.detect("Vamos a jugar Arena Breakout")
    assert req is not None
    assert (req.target_game, req.display_name) == ("abi", "Arena Breakout: Infinite")

    # Generic advisor
    req = detector.detect("Cambia a modo advisor")
    assert req is not None
    assert (req.target_game, req.display_name) == ("generic", "Game Advisor Universal")

    # Arbitrary games
    req = detector.detect("Vamos a jugar Once Human")
    assert req is not None
    assert (req.target_game, req.display_name) == ("once_human", "Once Human")

    req = detector.detect("Cambiemos a Elden Ring!")
    assert req is not None
    assert (req.target_game, req.display_name) == ("elden_ring", "Elden Ring")

    # Regular question should return None
    assert detector.detect("¿Qué munición uso?") is None


def test_switch_context_bootstraps_and_activates(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    orchestrator = AdvisorOrchestrator(config=cfg, db=db, provider=DummyProvider())
    assert orchestrator.active_context_id == "generic"

    # Switch to once_human
    ctx = orchestrator.switch_context("once_human", "Once Human")
    assert ctx.context_id == "once_human"
    assert ctx.display_name == "Once Human"
    assert ctx.archetype_id == "survival_craft"
    assert ctx.is_active is True

    # Orchestrator state updated
    assert orchestrator.active_context_id == "once_human"
    assert orchestrator.config.gemini.game == "once_human"
    assert orchestrator.memory.default_game == "once_human"
    assert orchestrator.rag.default_game == "once_human"

    # Dynamic archetype system prompt loaded
    system_inst = orchestrator.get_system_instruction()
    assert "Supervivencia y Crafteo" in system_inst or "survival" in system_inst.lower() or "once human" in system_inst.lower()


def test_verbal_context_switch_via_ask(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    dummy = DummyProvider()
    orchestrator = AdvisorOrchestrator(config=cfg, db=db, provider=dummy)

    # Ask with verbal trigger
    response = orchestrator.ask("¡Vamos a jugar Palworld!")

    assert "Palworld" in response.spoken_text
    assert orchestrator.active_context_id == "palworld"
    assert response.report_path is not None
    assert Path(response.report_path).is_file()

    # Verify dummy provider was not invoked (handled instantly without LLM latency)
    assert dummy.last_system_instruction is None

    # Next regular question uses the newly bootstrapped Palworld context prompt
    orchestrator.ask("¿Dónde consigo madera?")
    assert dummy.last_system_instruction is not None
    assert "Palworld" in dummy.last_system_instruction
