"""Focused unit tests for MetaTuning modularization (Etapa 3).

Verifies ConfigMutator, IntentParser, ClarificationFSM, Engine facade,
backward compatibility, thread-safety, atomic persistence, and strict LOC constraints.
"""

from pathlib import Path
import threading
import time
import pytest
import yaml

from abi_coach.application.services.config_mutator import ConfigMutator
from abi_coach.application.slices.archetypes.manager import ArchetypeManager
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.slices.metatuning.clarification_fsm import (
    CANCELLATION_PHRASES,
    CLARIFICATION_TTL_SEC,
    ClarificationFSM,
    ClarificationResolution,
    ClarificationState,
    is_cancellation_phrase,
)
from abi_coach.application.slices.metatuning.engine import MetaTuningEngine, MetaTuningResult
from abi_coach.application.slices.metatuning.intent_parser import (
    IntentParser,
    ParsedConfig,
    ParsedFact,
    ParsedRule,
)
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.config.settings import AppConfig


# ---------------------------------------------------------------------------
# 1. ConfigMutator Unit Tests
# ---------------------------------------------------------------------------

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

    # Non-existent or invalid key path gracefully fails without crashing
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

    # Mutate speaker.voice
    success = mutator.mutate(["speaker", "voice"], "es-CO-SalomeNeural")
    assert success is True
    assert cfg.speaker.voice == "es-CO-SalomeNeural"

    # Verify YAML content on disk preserved listener.mode and updated voice
    data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert data["speaker"]["voice"] == "es-CO-SalomeNeural"
    assert data["speaker"]["engine"] == "edge-tts"
    assert data["listener"]["mode"] == "continuous"
    assert data["listener"]["ptt_key"] == "f9"

    # Verify no dangling temp files remain
    tmp_files = list(tmp_path.glob("*.tmp*"))
    assert len(tmp_files) == 0


def test_config_mutator_resilience_and_edge_cases(tmp_path: Path):
    """Verify ConfigMutator handles non-existent files and invalid paths gracefully."""
    missing_file = tmp_path / "missing.yaml"
    mutator = ConfigMutator(config_path=str(missing_file))

    # Should return False gracefully when file does not exist
    assert mutator.save_key(["speaker", "voice"], "test") is False
    assert mutator.mutate([], "test") is False
    assert mutator.mutate([""], "test") is False
    assert mutator.mutate([None], "test") is False


# ---------------------------------------------------------------------------
# 2. IntentParser Unit Tests
# ---------------------------------------------------------------------------

def test_intent_parser_classification_and_heuristics():
    """Verify IntentParser detects intents and distinguishes vague from actionable prompts."""
    parser = IntentParser()

    # Intent detection
    assert parser.detect_intent("Configuración global cambia la voz a Salomé") == "config"
    assert parser.detect_intent("A partir de ahora prioriza siempre el loot morado") == "rule"
    assert parser.detect_intent("Cambia tu prompt para ser más táctico") == "prompt"
    assert parser.detect_intent("Registra que el rifle MDR tiene 45 de daño") == "rag"
    assert parser.detect_intent("¿Cómo está el clima?") is None

    # Vagueness heuristics
    assert parser.is_vague("Haz que el coach sea más inteligente con el loot") is True
    assert parser.is_vague("Ayúdame mejor") is True
    assert parser.is_vague("A partir de ahora solo avísame de munición Tier 4") is False
    assert parser.is_vague("Configuración global pon la tecla en F8") is False


def test_intent_parser_config_and_rule_parsing():
    """Verify IntentParser extracts parameters for config changes and rule observations."""
    parser = IntentParser()

    # Config parsing
    voice_cfg = parser.parse_config("cambiar configuración pon la voz a Elvira")
    assert voice_cfg is not None
    assert voice_cfg.key_path == ["speaker", "voice"]
    assert voice_cfg.value == "es-ES-ElviraNeural"
    assert voice_cfg.key_name == "speaker.voice"

    ptt_cfg = parser.parse_config("cambiar ptt a f11")
    assert ptt_cfg is not None
    assert ptt_cfg.key_path == ["listener", "ptt_key"]
    assert ptt_cfg.value == "f11"

    provider_nvidia = parser.parse_config("usar nvidia como proveedor")
    assert provider_nvidia is not None
    assert provider_nvidia.key_path == ["llm", "provider"]
    assert provider_nvidia.value == "nvidia"

    provider_gemini = parser.parse_config("usar gemini como proveedor")
    assert provider_gemini is not None
    assert provider_gemini.key_path == ["llm", "provider"]
    assert provider_gemini.value == "gemini"

    assert parser.parse_config("pregunta no relacionada") is None

    # Rule parsing
    parsed_rule = parser.parse_rule("A partir de ahora descarta siempre el loot gris")
    assert parsed_rule.what == "descarta siempre el loot gris"
    assert "Loot Gris" in parsed_rule.title
    assert parsed_rule.slug != ""

    # Category detection
    assert parser.detect_category("optimiza mi alijo") == "loot"
    assert parser.detect_category("asistencia en pelea de arma corta") == "combat"
    assert parser.detect_category("cambia el audio y habla breve") == "voice"
    assert parser.detect_category("otra cosa aleatoria") == "general"

    # RAG fact parsing
    fact_weapon = parser.parse_rag_fact("El rifle M4A1 usa calibre 5.56")
    assert fact_weapon.category == "weapon"
    fact_ammo = parser.parse_rag_fact("La bala M80 perfora blindaje clase 4")
    assert fact_ammo.category == "ammo"
    fact_loot = parser.parse_rag_fact("El objeto León Dorado vale 150k")
    assert fact_loot.category == "loot"


def test_intent_parser_cancellation_and_resolution():
    """Verify IntentParser cancellation detection and clarification response resolution."""
    parser = IntentParser()

    assert parser.is_cancellation("cancela") is True
    assert parser.is_cancellation("olvídalo") is True
    assert parser.is_cancellation("no importa") is True
    assert parser.is_cancellation("¡Cancela por favor!") is True
    assert parser.is_cancellation("quiero continuar") is False

    rule_loot = parser.parse_clarification_resolution("Prioriza el valor por casilla", category="loot")
    assert rule_loot.slug == "loot_value_per_slot"

    rule_ammo = parser.parse_clarification_resolution("Penetración máxima contra blindajes", category="combat")
    assert rule_ammo.slug == "max_penetration"

    rule_custom = parser.parse_clarification_resolution("haz algo completamente personalizado", category="combat")
    assert "Personalizada" in rule_custom.title


# ---------------------------------------------------------------------------
# 3. ClarificationFSM Unit Tests
# ---------------------------------------------------------------------------

def test_clarification_fsm_lifecycle_and_ttl():
    """Verify ClarificationFSM handles transitions, 60s TTL, and cancellation phrases."""
    fsm = ClarificationFSM(ttl_sec=60.0)
    assert fsm.has_pending is False
    assert fsm.pending is None

    # Start pending clarification
    state = fsm.start("Haz que el coach sea mejor con el loot", context_id="abi", category="loot")
    assert fsm.has_pending is True
    assert state.category == "loot"
    assert state.timestamp == state.created_at
    assert state.get("timestamp") == state.created_at
    assert state["category"] == "loot"

    # Cancellation check
    assert fsm.is_cancellation("cancela") is True
    assert fsm.is_cancellation("olvídalo") is True
    assert fsm.is_cancellation("no importa") is True
    assert fsm.is_cancellation("sí, continúa") is False

    # Expiration check
    assert fsm.is_expired() is False
    state.created_at = time.time() - 65.0
    assert fsm.is_expired() is True

    # Auto reset on expiration
    assert fsm.is_expired(auto_reset=True) is True
    assert fsm.has_pending is False
    assert fsm.pending is None

    # Clear / reset
    fsm.start("Otro prompt")
    assert fsm.has_pending is True
    fsm.clear()
    assert fsm.has_pending is False


def test_clarification_fsm_resolution_mapping():
    """Verify user responses resolve to predefined tactical rules."""
    fsm = ClarificationFSM()
    fsm.start("loot vago", context_id="abi", category="loot")

    old_state, res1 = fsm.resolve("Prioriza el valor por casilla")
    assert res1.slug == "loot_value_per_slot"
    assert "Casilla" in res1.title
    assert fsm.has_pending is False

    fsm.start("combate vago", context_id="abi", category="combat")
    old_state, res2 = fsm.resolve("Penetración máxima contra blindajes")
    assert res2.slug == "max_penetration"
    assert fsm.has_pending is False


def test_clarification_fsm_thread_safety():
    """Verify ClarificationFSM transitions are thread-safe under concurrent operations."""
    fsm = ClarificationFSM()
    errors = []

    def worker(idx: int):
        try:
            for _ in range(50):
                fsm.start_clarification(f"Prompt {idx}", context_id="abi", category="combat")
                _ = fsm.has_pending
                _ = fsm.is_expired()
                _ = fsm.resolve("penetración máxima")
                fsm.reset()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


# ---------------------------------------------------------------------------
# 4. MetaTuningEngine Facade & Backward Compatibility Tests
# ---------------------------------------------------------------------------

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

    # pending_clarification getter / setter property
    assert engine.pending_clarification is None
    new_state = ClarificationState("prompt", "generic", "loot", time.time())
    engine.pending_clarification = new_state
    assert engine.pending_clarification == new_state
    assert isinstance(engine.pending_clarification, ClarificationState)
    engine.pending_clarification = None
    assert engine.pending_clarification is None

    # _save_config_key compatibility
    engine._save_config_key(["speaker", "voice"], "es-MX-DaliaNeural")
    saved_data = yaml.safe_load(cfg_yaml.read_text(encoding="utf-8"))
    assert saved_data["speaker"]["voice"] == "es-MX-DaliaNeural"

    # Backward compatibility handler aliases
    res_cfg = engine._handle_config_update("Configuración global cambia la voz a Salomé")
    assert res_cfg.action_taken == "config_updated"

    res_rag = engine._handle_rag_fact("Registra que el rifle MDR usa balas 7.62x51", context_id="generic")
    assert res_rag.action_taken == "rag_ingested"

    res_rule = engine._handle_rule_creation("A partir de ahora no compres granadas", context_id="generic")
    assert res_rule.action_taken == "rule_saved"

    # process_turn is alias of process
    res_turn = engine.process_turn("A partir de ahora no compres chalecos", context_id="generic")
    assert res_turn is not None
    assert res_turn.action_taken == "rule_saved"


# ---------------------------------------------------------------------------
# 5. Strict LOC Compliance Tests
# ---------------------------------------------------------------------------

def test_modularization_loc_limits():
    """Verify all refactored modules satisfy strict LOC budget criteria."""
    project_root = Path(__file__).resolve().parent.parent

    mutator_path = project_root / "src" / "abi_coach" / "application" / "services" / "config_mutator.py"
    engine_path = project_root / "src" / "abi_coach" / "application" / "slices" / "metatuning" / "engine.py"
    parser_path = project_root / "src" / "abi_coach" / "application" / "slices" / "metatuning" / "intent_parser.py"
    fsm_path = project_root / "src" / "abi_coach" / "application" / "slices" / "metatuning" / "clarification_fsm.py"

    assert mutator_path.is_file(), f"{mutator_path} does not exist"
    mutator_loc = len(mutator_path.read_text(encoding="utf-8").splitlines())
    assert mutator_loc < 90, f"config_mutator.py exceeded 90 LOC ({mutator_loc} lines)"

    assert engine_path.is_file(), f"{engine_path} does not exist"
    engine_loc = len(engine_path.read_text(encoding="utf-8").splitlines())
    assert engine_loc <= 140, f"engine.py exceeded 140 LOC ({engine_loc} lines)"

    assert parser_path.is_file(), f"{parser_path} does not exist"
    parser_loc = len(parser_path.read_text(encoding="utf-8").splitlines())
    assert parser_loc < 100, f"intent_parser.py exceeded 100 LOC ({parser_loc} lines)"

    assert fsm_path.is_file(), f"{fsm_path} does not exist"
    fsm_loc = len(fsm_path.read_text(encoding="utf-8").splitlines())
    assert fsm_loc < 100, f"clarification_fsm.py exceeded 100 LOC ({fsm_loc} lines)"
