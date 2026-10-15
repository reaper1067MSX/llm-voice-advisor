"""Unit tests for hot context switching and Advisor onboarding configurator."""

from pathlib import Path
import pytest

from abi_coach.brain import Brain
from abi_coach.config import AppConfig
from abi_coach.db import DatabaseManager
from abi_coach.providers.base import ProviderResponse


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


def test_detect_context_switch_request(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    brain = Brain(config=cfg, db=db, provider=DummyProvider())

    # Extraction shooter
    res = brain.detect_context_switch_request("Vamos a jugar Arena Breakout")
    assert res == ("abi", "Arena Breakout: Infinite")

    # Generic advisor
    res = brain.detect_context_switch_request("Cambia a modo advisor")
    assert res == ("generic", "Game Advisor Universal")

    # Arbitrary games
    res = brain.detect_context_switch_request("Vamos a jugar Once Human")
    assert res == ("once_human", "Once Human")

    res = brain.detect_context_switch_request("Cambiemos a Elden Ring!")
    assert res == ("elden_ring", "Elden Ring")

    res = brain.detect_context_switch_request("Inicia contexto para Rust")
    assert res == ("rust", "Rust")

    # Regular question should return None
    assert brain.detect_context_switch_request("¿Qué munición uso?") is None


def test_switch_context_bootstraps_and_activates(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    brain = Brain(config=cfg, db=db, provider=DummyProvider())
    assert brain.active_context_id == "generic"

    # Switch to once_human
    ctx = brain.switch_context("once_human", "Once Human")
    assert ctx.context_id == "once_human"
    assert ctx.display_name == "Once Human"
    assert ctx.archetype_id == "survival_craft"
    assert ctx.is_active is True

    # Brain state updated
    assert brain.active_context_id == "once_human"
    assert brain.config.gemini.game == "once_human"
    assert brain.memory.default_game == "once_human"
    assert brain.rag.default_game == "once_human"

    # Context history turn appended
    assert any("Contexto cambiado a Once Human" in turn.text for turn in brain.history)

    # Dynamic archetype system prompt loaded
    system_inst = brain.get_system_instruction()
    assert "Supervivencia y Crafteo" in system_inst or "survival" in system_inst.lower() or "once human" in system_inst.lower()


def test_verbal_context_switch_via_ask(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    dummy = DummyProvider()
    brain = Brain(config=cfg, db=db, provider=dummy)

    # Ask with verbal trigger
    response = brain.ask("¡Vamos a jugar Palworld!")

    assert "Palworld" in response.spoken_text
    assert brain.active_context_id == "palworld"
    assert response.report_path is not None
    assert Path(response.report_path).is_file()

    # Verify dummy provider was not invoked (handled instantly without LLM latency)
    assert dummy.last_system_instruction is None

    # Next regular question uses the newly bootstrapped Palworld context prompt
    brain.ask("¿Dónde consigo madera?")
    assert dummy.last_system_instruction is not None
    assert "Palworld" in dummy.last_system_instruction
