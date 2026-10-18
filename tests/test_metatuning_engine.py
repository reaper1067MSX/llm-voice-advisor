"""Focused unit tests for MetaTuningEngine facade."""

from pathlib import Path
import time
import pytest
import yaml

from abi_coach.application.slices.archetypes.manager import ArchetypeManager
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.slices.metatuning.clarification_fsm import ClarificationState
from abi_coach.application.slices.metatuning.engine import MetaTuningEngine
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.config.settings import AppConfig


def test_facade_delegation_and_properties(tmp_path: Path):
    """Verify MetaTuningEngine facade orchestrates subcomponents and maintains compatibility."""
    db = DatabaseManager(str(tmp_path / "facade.db"))
    mgr = ArchetypeManager(db)
    scaffolder = ArchetypeScaffolder(db, mgr)
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False
    cfg_yaml = tmp_path / "config.yaml"
    cfg_yaml.write_text("speaker:\n  voice: es-CO-SalomeNeural\n", encoding="utf-8")

    engine = MetaTuningEngine(
        db=db,
        archetype_mgr=mgr,
        scaffolder=scaffolder,
        config=cfg,
        config_path=str(cfg_yaml),
    )

    assert engine.pending_clarification is None
    new_state = ClarificationState("prompt", "generic", "loot", time.time())
    engine.pending_clarification = new_state
    assert engine.pending_clarification == new_state
    assert isinstance(engine.pending_clarification, ClarificationState)
    engine.pending_clarification = None
    assert engine.pending_clarification is None

    engine._save_config_key(["speaker", "voice"], "es-MX-DaliaNeural")
    saved_data = yaml.safe_load(cfg_yaml.read_text(encoding="utf-8"))
    assert saved_data["speaker"]["voice"] == "es-MX-DaliaNeural"

    res_cfg = engine._handle_config_update("Configuración global cambia la voz a Salomé")
    assert res_cfg.action_taken == "config_updated"

    res_rag = engine._handle_rag_fact("Registra que el rifle MDR usa balas 7.62x51", context_id="generic")
    assert res_rag.action_taken == "rag_ingested"

    res_rule = engine._handle_rule_creation("A partir de ahora no compres granadas", context_id="generic")
    assert res_rule.action_taken == "rule_saved"

    res_turn = engine.process_turn("A partir de ahora no compres chalecos", context_id="generic")
    assert res_turn is not None
    assert res_turn.action_taken == "rule_saved"
