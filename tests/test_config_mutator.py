"""Focused unit tests for ConfigMutator (Application Service)."""

from pathlib import Path
import pytest
import yaml

from abi_coach.application.services.config_mutator import ConfigMutator
from abi_coach.infrastructure.config.settings import AppConfig


def test_config_mutator_in_memory_update():
    """Verify ConfigMutator updates nested fields on in-memory AppConfig."""
    cfg = AppConfig()
    mutator = ConfigMutator(config=cfg)

    assert mutator._update_in_memory(["speaker", "voice"], "es-ES-ElviraNeural") is True
    assert cfg.speaker.voice == "es-ES-ElviraNeural"

    assert mutator._update_in_memory(["listener", "ptt_key"], "f12") is True
    assert cfg.listener.ptt_key == "f12"

    assert mutator._update_in_memory(["llm", "provider"], "nvidia") is True
    assert cfg.llm.provider == "nvidia"

    assert mutator._update_in_memory(["invalid_section", "no_key"], "val") is False
    assert mutator._update_in_memory([], "val") is False


def test_config_mutator_atomic_file_persistence(tmp_path: Path):
    """Verify ConfigMutator atomically updates YAML and preserves existing properties."""
    yaml_file = tmp_path / "config.yaml"
    initial_content = """
speaker:
  engine: "edge-tts"
  voice: "es-MX-DaliaNeural"
listener:
  ptt_key: "f9"
  mode: "continuous"
llm:
  provider: "gemini"
"""
    yaml_file.write_text(initial_content, encoding="utf-8")
    cfg = AppConfig()
    mutator = ConfigMutator(config_path=str(yaml_file), config=cfg)

    success = mutator.mutate(["speaker", "voice"], "es-CO-SalomeNeural")
    assert success is True
    assert cfg.speaker.voice == "es-CO-SalomeNeural"

    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert data["speaker"]["voice"] == "es-CO-SalomeNeural"
    assert data["speaker"]["engine"] == "edge-tts"
    assert data["listener"]["mode"] == "continuous"
    assert data["listener"]["ptt_key"] == "f9"

    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert len(tmp_files) == 0


def test_config_mutator_resilience_and_edge_cases(tmp_path: Path):
    """Verify ConfigMutator handles non-existent files and invalid paths gracefully."""
    missing_file = tmp_path / "missing.yaml"
    mutator = ConfigMutator(config_path=str(missing_file))

    assert mutator.save_key(["speaker", "voice"], "test") is False
    assert mutator.mutate([], "test") is False
    assert mutator.mutate([""], "test") is False
    assert mutator.mutate([None], "test") is False
