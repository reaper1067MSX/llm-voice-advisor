"""Unit tests for Conversational Meta-Tuning Engine and Clarification Loop."""

from pathlib import Path
import pytest
import yaml

from abi_coach.archetypes import ArchetypeManager
from abi_coach.brain import Brain
from abi_coach.config import AppConfig
from abi_coach.db import DatabaseManager
from abi_coach.metatuning import MetaTuningEngine
from abi_coach.providers.base import ProviderResponse
from abi_coach.scaffolding import ArchetypeScaffolder


class DummyProvider:
    def __init__(self):
        self.call_count = 0
        self.last_prompt = None

    def generate(
        self,
        prompt,
        system_instruction,
        image_bytes=None,
        crop_bytes=None,
        history_text=None,
        tool_callback=None,
    ):
        self.call_count += 1
        self.last_prompt = prompt
        return ProviderResponse(spoken_text="Normal LLM advice", input_tokens=10, output_tokens=10)


def test_detect_intent_and_vagueness(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    mgr = ArchetypeManager(db)
    scaffolder = ArchetypeScaffolder(db, mgr)
    cfg = AppConfig()

    engine = MetaTuningEngine(db=db, archetype_mgr=mgr, scaffolder=scaffolder, config=cfg)

    # Intent detection
    assert engine.detect_intent("Configuración global cambia la voz a Salomé") == "config"
    assert engine.detect_intent("A partir de ahora descarta munición Tier 3") == "rule"
    assert engine.detect_intent("Cambia tu prompt para ser más táctico") == "prompt"
    assert engine.detect_intent("Registra que el rifle MDR tiene 45 de daño") == "rag"
    assert engine.detect_intent("¿Qué penetración tiene la M80?") is None

    # Vagueness evaluation
    assert engine.is_vague("Haz que el coach sea más inteligente con el loot") is True
    assert engine.is_vague("Ayúdame mejor con el combate") is True
    assert engine.is_vague("Quiero que seas mejor") is True
    assert engine.is_vague("A partir de ahora solo avísame de munición Tier 4 o superior") is False
    assert engine.is_vague("Configuración global cambia la tecla a F8") is False


def test_clarification_loop_multi_turn(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    mgr = ArchetypeManager(db)
    scaffolder = ArchetypeScaffolder(db, mgr)
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    engine = MetaTuningEngine(db=db, archetype_mgr=mgr, scaffolder=scaffolder, config=cfg)

    # Turn 1: Vague request
    res1 = engine.process("Haz que el coach sea más inteligente con el loot", context_id="abi")
    assert res1 is not None
    assert res1.action_taken == "clarification_needed"
    assert res1.is_clarification is True
    assert "criterio de loot" in res1.spoken_response
    assert "¿Deseas que priorice el valor económico por casilla" in res1.spoken_response
    assert engine.pending_clarification is not None

    # Turn 2: User clarification response
    res2 = engine.process("Prioriza el valor por casilla", context_id="abi")
    assert res2 is not None
    assert res2.action_taken == "rule_saved"
    assert res2.is_clarification is False
    assert "Prioridad de Loot por Casilla" in res2.spoken_response
    assert engine.pending_clarification is None

    # Verify rule persisted in engram_observations table
    con = db.get_connection()
    cur = con.cursor()
    cur.execute("SELECT topic_key, title, content FROM engram_observations WHERE context_id = 'abi';")
    rows = cur.fetchall()
    rule_keys = [r["topic_key"] for r in rows]
    assert any("loot_value_per_slot" in k for k in rule_keys)


def test_direct_unambiguous_rule_saving(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    mgr = ArchetypeManager(db)
    scaffolder = ArchetypeScaffolder(db, mgr)
    cfg = AppConfig()

    engine = MetaTuningEngine(db=db, archetype_mgr=mgr, scaffolder=scaffolder, config=cfg)

    res = engine.process("A partir de ahora descarta siempre las balas Tier 3", context_id="abi")
    assert res is not None
    assert res.action_taken == "rule_saved"
    assert res.is_clarification is False
    assert "Entendido. He registrado la regla" in res.spoken_response

    con = db.get_connection()
    cur = con.cursor()
    cur.execute("SELECT content FROM engram_observations WHERE context_id = 'abi';")
    contents = [r["content"] for r in cur.fetchall()]
    assert any("descarta siempre las balas Tier 3" in c for c in contents)


def test_global_config_tuning(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    mgr = ArchetypeManager(db)
    scaffolder = ArchetypeScaffolder(db, mgr)

    cfg_yaml = tmp_path / "config.yaml"
    cfg_yaml.write_text(
        """
speaker:
  voice: "es-MX-DaliaNeural"
listener:
  ptt_key: "f9"
llm:
  provider: "gemini"
""",
        encoding="utf-8",
    )

    cfg = AppConfig()
    cfg.speaker.voice = "es-MX-DaliaNeural"
    cfg.listener.ptt_key = "f9"

    engine = MetaTuningEngine(
        db=db,
        archetype_mgr=mgr,
        scaffolder=scaffolder,
        config=cfg,
        config_path=str(cfg_yaml),
    )

    # 1. Change voice
    res_voice = engine.process("Configuración global cambia la voz a Salomé", context_id="generic")
    assert res_voice.action_taken == "config_updated"
    assert cfg.speaker.voice == "es-CO-SalomeNeural"

    saved_data = yaml.safe_load(cfg_yaml.read_text(encoding="utf-8"))
    assert saved_data["speaker"]["voice"] == "es-CO-SalomeNeural"

    # 2. Change PTT key
    res_ptt = engine.process("Configuración global pon la tecla en F8", context_id="generic")
    assert res_ptt.action_taken == "config_updated"
    assert cfg.listener.ptt_key == "f8"

    saved_data = yaml.safe_load(cfg_yaml.read_text(encoding="utf-8"))
    assert saved_data["listener"]["ptt_key"] == "f8"


def test_brain_ask_metatuning_integration(tmp_path: Path):
    db_file = tmp_path / "test.sqlite3"
    db = DatabaseManager(str(db_file))
    cfg = AppConfig()
    cfg.reports.output_dir = str(tmp_path / "reports")
    cfg.reports.auto_open_browser = False

    dummy = DummyProvider()
    brain = Brain(config=cfg, db=db, provider=dummy)

    # Step 1: Send ambiguous prompt
    r1 = brain.ask("Haz que el coach sea más inteligente con el loot")
    assert dummy.call_count == 0  # Zero LLM latency, handled by Clarification Loop
    assert "¿Deseas que priorice" in r1.spoken_text

    # Step 2: Clarification response
    r2 = brain.ask("Filtra solo objetos morados o dorados")
    assert dummy.call_count == 0
    assert "Filtro de Objetos de Alto Tier" in r2.spoken_text
    assert r2.report_path is not None

    # Step 3: Regular in-game question delegates to LLM provider
    r3 = brain.ask("¿Qué chaleco me compro para Granja?")
    assert dummy.call_count == 1
    assert r3.spoken_text == "Normal LLM advice"
