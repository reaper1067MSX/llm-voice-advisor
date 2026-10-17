"""Unit tests for Brain thin facade backward compatibility and delegation."""

from pathlib import Path

from abi_coach.application.orchestration.brain import Brain
from abi_coach.domain.common.result import Success
from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.config.settings import AppConfig


class EchoProvider:
    def generate(self, prompt, system_instruction, **kwargs):
        return ProviderResponse(
            spoken_text=f"Echo: {prompt}",
            input_tokens=10,
            output_tokens=5,
            latency_ms=12.0,
        )


def test_brain_facade_backward_compatibility(tmp_path: Path):
    """Verify Brain thin facade exposes expected attributes, properties, and delegating methods."""
    cfg = AppConfig()
    cfg.gemini.api_key = "dummy-key"
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False
    db = DatabaseManager(str(tmp_path / "brain.db"))

    brain = Brain(config=cfg, db=db, provider=EchoProvider())

    assert brain.current_game == "generic"
    brain.current_game = "abi"
    assert brain.active_context_id == "abi"

    # Context switch delegation
    ctx = brain.switch_context("once_human", "Once Human")
    assert ctx.context_id == "once_human"
    assert brain.current_game == "once_human"

    # ask and ask_result delegation
    res = brain.ask("Hola copiloto")
    assert res.spoken_text == "Echo: Hola copiloto"

    res_result = brain.ask_result("Consulta de prueba")
    assert isinstance(res_result, Success)
    assert res_result.unwrap().spoken_text == "Echo: Consulta de prueba"
