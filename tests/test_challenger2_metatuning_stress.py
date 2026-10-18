"""Adversarial stress testing and empirical verification suite for Etapa 3 (MetaTuning).

Authored by Challenger 2 (Empirical Adversarial Verifier).
Stress-tests IntentParser, ClarificationFSM, ConfigMutator, and MetaTuningEngine facade
under adversarial, boundary, concurrent, malformed, and error conditions.
"""

import os
from pathlib import Path
import stat
import threading
import time
from unittest.mock import patch
import pytest
import yaml

from abi_coach.application.services.config_mutator import ConfigMutator
from abi_coach.application.slices.archetypes.manager import ArchetypeManager
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.slices.metatuning.clarification_fsm import (
    CLARIFICATION_TTL_SEC,
    ClarificationFSM,
    ClarificationState,
    is_cancellation_phrase,
)
from abi_coach.application.slices.metatuning.engine import MetaTuningEngine, MetaTuningResult
from abi_coach.application.slices.metatuning.intent_parser import IntentParser
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.config.settings import AppConfig


# ===========================================================================
# 1. IntentParser Adversarial Stress Tests
# ===========================================================================

class TestIntentParserAdversarial:
    """Adversarial and boundary stress tests for IntentParser."""

    @pytest.fixture
    def parser(self):
        return IntentParser()

    def test_empty_and_whitespace_prompts(self, parser):
        """Verify parser handles empty, whitespace, and unicode blank strings safely."""
        blank_inputs = [
            "",
            "   ",
            "\t\n\r",
            " \u200b\u3000 ",  # Zero-width space and ideographic fullwidth space
            "\n\n\n\t\t\t",
        ]
        for inp in blank_inputs:
            assert parser.detect_intent(inp) is None
            assert parser.is_vague(inp) is False
            assert parser.is_cancellation(inp) is False
            assert parser.detect_category(inp) == "general"
            assert parser.parse_config(inp) is None

            rule = parser.parse_rule(inp)
            assert rule.title != ""
            assert isinstance(rule.slug, str)

            res = parser.parse_clarification_resolution(inp, category="general")
            assert res.slug != ""

            fact = parser.parse_rag_fact(inp)
            assert fact.category == "equipment"

    def test_malformed_symbols_and_control_chars(self, parser):
        """Verify parser handles punctuation-only, null bytes, and control characters."""
        malformed_inputs = [
            ":::...---///???!$#%^&*",
            "¡¿!?!?;:,,,....",
            "cambiar configuracion\x00voz a salome",
            "\x01\x02\x03\x04\x05\x06\x07",
            "🎯🚀🔥💀🎮⚔️",
            "SELECT * FROM users WHERE '1'='1';",
            "<script>alert('xss')</script>",
            "%s %d {0} {{}}",
        ]
        for inp in malformed_inputs:
            # None of these calls should raise an unhandled exception
            _ = parser.detect_intent(inp)
            _ = parser.is_vague(inp)
            _ = parser.is_cancellation(inp)
            _ = parser.detect_category(inp)
            _ = parser.parse_config(inp)
            rule = parser.parse_rule(inp)
            assert isinstance(rule.title, str)
            assert isinstance(rule.slug, str)

    def test_extremely_large_prompt_stress(self, parser):
        """Verify parser does not suffer from catastrophic regex backtracking or crash on 100k chars."""
        huge_prompt = ("cambiar configuracion pon la voz a salome " * 2000) + " regla extra " * 1000
        assert len(huge_prompt) > 80000

        t0 = time.perf_counter()
        intent = parser.detect_intent(huge_prompt)
        vague = parser.is_vague(huge_prompt)
        cfg = parser.parse_config(huge_prompt)
        rule = parser.parse_rule(huge_prompt)
        t_elapsed = time.perf_counter() - t0

        assert intent == "config"
        assert cfg is not None
        assert cfg.value == "es-CO-SalomeNeural"
        assert len(rule.slug) <= 30
        # Execution must be fast (< 0.25 seconds) — guarantees no ReDoS
        assert t_elapsed < 0.25, f"Parsing took too long ({t_elapsed:.4f}s), possible ReDoS!"

    def test_ptt_key_boundary_parsing(self, parser):
        """Verify F1-F12 boundary detection and rejection of invalid function keys."""
        # Valid bounds: F1 to F12
        for i in range(1, 13):
            prompt = f"configuración global cambiar ptt a f{i}"
            parsed = parser.parse_config(prompt)
            assert parsed is not None, f"Failed for F{i}"
            assert parsed.value == f"f{i}"
            assert parsed.key_path == ["listener", "ptt_key"]

        # Invalid bounds: F0, F13, F14, F99, F100
        for invalid_f in ["f0", "f13", "f14", "f99", "f100", "f1a"]:
            prompt = f"configuración global cambiar ptt a {invalid_f}"
            parsed = parser.parse_config(prompt)
            assert parsed is None, f"Should reject invalid key {invalid_f}"

    def test_voice_map_coverage_and_accents(self, parser):
        """Verify all 9 catalog voices, accents, and case variations parse correctly."""
        voices = {
            "salome": "es-CO-SalomeNeural",
            "salomé": "es-CO-SalomeNeural",
            "elvira": "es-ES-ElviraNeural",
            "ximena": "es-ES-XimenaNeural",
            "camila": "es-PE-CamilaNeural",
            "paloma": "es-US-PalomaNeural",
            "dalia": "es-MX-DaliaNeural",
            "elena": "es-AR-ElenaNeural",
            "catalina": "es-CL-CatalinaNeural",
        }
        for v_name, expected_id in voices.items():
            # Test lowercase
            prompt1 = f"ajustes globales cambiar voz a {v_name}"
            p1 = parser.parse_config(prompt1)
            assert p1 is not None and p1.value == expected_id

            # Test uppercase
            prompt2 = f"CONFIGURACION GLOBAL PON LA VOZ DE {v_name.upper()}"
            p2 = parser.parse_config(prompt2)
            assert p2 is not None and p2.value == expected_id

    def test_cancellation_phrases_variations(self, parser):
        """Verify exact and sentence-embedded cancellation detection."""
        cancellations = [
            "cancela",
            "cancelar",
            "olvídalo",
            "olvidalo",
            "no importa",
            "¡Cancela!",
            "Por favor, cancela la operación.",
            "Olvídalo, no quiero cambiar nada.",
            "no importa, déjalo como estaba",
        ]
        for c in cancellations:
            assert parser.is_cancellation(c) is True, f"Failed to detect cancellation: '{c}'"

        non_cancellations = [
            "quiero continuar",
            "prioriza el loot de alto tier",
            "no pares",
            "cancion nueva",
        ]
        for nc in non_cancellations:
            assert parser.is_cancellation(nc) is False, f"False positive cancellation on: '{nc}'"


# ===========================================================================
# 2. ClarificationFSM Concurrency, Race Conditions & TTL Stress Tests
# ===========================================================================

class TestClarificationFSMStress:
    """Stress testing ClarificationFSM with TTL boundaries, state cycling, and threading."""

    def test_ttl_boundary_exact_precision(self):
        """Verify strict TTL behavior at 59s, 60s, and 61s boundaries."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        t_base = 1000000.0

        fsm.start("loot vago", context_id="abi", category="loot")
        fsm.pending.created_at = t_base

        # 1. Boundary at 59.0s -> Active
        assert fsm.is_expired(now=t_base + 59.0) is False

        # 2. Boundary at 59.999s -> Active
        assert fsm.is_expired(now=t_base + 59.999) is False

        # 3. Boundary at exact 60.0s -> Active (since > 60.0 is False)
        assert fsm.is_expired(now=t_base + 60.0) is False

        # 4. Boundary at 60.001s -> Expired
        assert fsm.is_expired(now=t_base + 60.001) is True

        # 5. Boundary at 61.0s -> Expired
        assert fsm.is_expired(now=t_base + 61.0) is True

    def test_ttl_auto_reset_behavior(self):
        """Verify is_expired(auto_reset=True) resets state on expiration but preserves when active."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        t_base = 2000000.0

        fsm.start("loot vago", context_id="abi", category="loot")
        fsm.pending.created_at = t_base

        # When active at 59s: auto_reset should NOT wipe state
        assert fsm.is_expired(now=t_base + 59.0, auto_reset=True) is False
        assert fsm.has_pending is True
        assert fsm.pending is not None

        # When expired at 61s: auto_reset MUST wipe state atomically
        assert fsm.is_expired(now=t_base + 61.0, auto_reset=True) is True
        assert fsm.has_pending is False
        assert fsm.pending is None

    def test_fsm_empty_state_resilience(self):
        """Verify FSM methods execute safely without crash when no state is pending."""
        fsm = ClarificationFSM()
        assert fsm.has_pending is False
        assert fsm.is_expired() is False

        # Resolving without pending should return fallback rule safely
        old_state, res = fsm.resolve("Prioriza el valor por casilla")
        assert old_state is None
        assert res.slug == "loot_value_per_slot"

        # Calling reset/clear on empty state should be a clean no-op
        fsm.reset()
        fsm.clear()
        assert fsm.has_pending is False

    def test_fsm_legacy_dict_and_timestamp_attribute_support(self):
        """Verify backward compatibility with legacy dict-based or timestamp-based state."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        t_now = time.time()

        # Legacy dict with created_at
        fsm.pending = {"created_at": t_now - 65.0, "category": "loot"}
        assert fsm.is_expired() is True

        # Legacy dict with timestamp
        fsm.pending = {"timestamp": t_now - 10.0, "category": "loot"}
        assert fsm.is_expired() is False

    def test_fsm_heavy_concurrency_and_race_conditions(self):
        """Verify thread-safety under heavy concurrent multi-threaded contention."""
        fsm = ClarificationFSM(ttl_sec=60.0)
        errors = []
        stop_event = threading.Event()

        def worker_start(idx: int):
            try:
                for i in range(150):
                    if stop_event.is_set():
                        break
                    fsm.start(f"Prompt {idx}_{i}", context_id="test", category="loot")
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def worker_resolve(idx: int):
            try:
                for _ in range(150):
                    if stop_event.is_set():
                        break
                    _ = fsm.resolve("Prioriza el valor por casilla")
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def worker_expired(idx: int):
            try:
                for _ in range(150):
                    if stop_event.is_set():
                        break
                    _ = fsm.is_expired(auto_reset=True)
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        def worker_reset(idx: int):
            try:
                for _ in range(150):
                    if stop_event.is_set():
                        break
                    fsm.reset()
                    time.sleep(0.0001)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(4):
            threads.append(threading.Thread(target=worker_start, args=(i,)))
            threads.append(threading.Thread(target=worker_resolve, args=(i,)))
            threads.append(threading.Thread(target=worker_expired, args=(i,)))
            threads.append(threading.Thread(target=worker_reset, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
            if t.is_alive():
                stop_event.set()
                pytest.fail("Thread deadlock detected in ClarificationFSM!")

        assert len(errors) == 0, f"Concurrent execution produced errors: {errors}"


# ===========================================================================
# 3. ConfigMutator Atomic Persistence & Fault Injection Tests
# ===========================================================================

class TestConfigMutatorStress:
    """Stress testing ConfigMutator under invalid YAML, read-only files, and deep paths."""

    def test_corrupted_yaml_resilience(self, tmp_path: Path):
        """Verify ConfigMutator fails safely on invalid YAML and leaves no temp files."""
        corrupted_file = tmp_path / "corrupted.yaml"
        corrupted_file.write_text("invalid: [yaml: unclosed syntax \x00", encoding="utf-8")

        mutator = ConfigMutator(config_path=str(corrupted_file))
        success = mutator.mutate(["speaker", "voice"], "es-ES-ElviraNeural")

        assert success is False
        # Corrupted file content must not be wiped out or mangled
        assert "invalid: [yaml: unclosed syntax" in corrupted_file.read_text(encoding="utf-8")
        # Ensure no orphan temporary files remained
        assert len(list(tmp_path.glob("*.tmp*"))) == 0

    def test_non_dict_yaml_content(self, tmp_path: Path):
        """Verify ConfigMutator handles YAML files containing lists, strings, or numbers."""
        test_cases = [
            "- list_item_1\n- list_item_2\n",
            "just a plain scalar string",
            "123456789",
            "",  # empty file
        ]
        for idx, content in enumerate(test_cases):
            cfg_file = tmp_path / f"non_dict_{idx}.yaml"
            cfg_file.write_text(content, encoding="utf-8")

            mutator = ConfigMutator(config_path=str(cfg_file))
            success = mutator.mutate(["speaker", "voice"], "es-MX-DaliaNeural")

            assert success is True
            # Should have gracefully converted to a dict with the specified key
            loaded = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
            assert isinstance(loaded, dict)
            assert loaded["speaker"]["voice"] == "es-MX-DaliaNeural"

    def test_read_only_config_file_resilience(self, tmp_path: Path):
        """Verify ConfigMutator handles read-only files gracefully without unhandled crashes."""
        ro_file = tmp_path / "readonly_config.yaml"
        ro_file.write_text("speaker:\n  voice: es-CO-SalomeNeural\n", encoding="utf-8")

        # Make file read-only on Windows / Unix
        os.chmod(ro_file, stat.S_IREAD)

        try:
            mutator = ConfigMutator(config_path=str(ro_file))
            # On Windows, replacing a read-only file triggers PermissionError
            success = mutator.mutate(["speaker", "voice"], "es-ES-ElviraNeural")
            # Must return False gracefully without raising unhandled exception
            assert success is False
            # Ensure no orphan temporary files remained
            assert len(list(tmp_path.glob("*.tmp*"))) == 0
        finally:
            # Restore write permission for cleanup
            os.chmod(ro_file, stat.S_IWRITE | stat.S_IREAD)

    def test_deep_nested_dictionary_mutation(self, tmp_path: Path):
        """Verify updating deeply nested keys (10 levels) and overcoming non-dict intermediates."""
        cfg_file = tmp_path / "deep_nested.yaml"
        # Level 3 is currently a string instead of a dict
        cfg_file.write_text("l1:\n  l2:\n    l3: 'string_blocker'\n", encoding="utf-8")

        mutator = ConfigMutator(config_path=str(cfg_file))
        deep_path = ["l1", "l2", "l3", "l4", "l5", "l6", "l7", "leaf_key"]
        success = mutator.mutate(deep_path, "deep_value")

        assert success is True
        data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
        assert data["l1"]["l2"]["l3"]["l4"]["l5"]["l6"]["l7"]["leaf_key"] == "deep_value"

    def test_atomic_write_failure_cleanup(self, tmp_path: Path):
        """Verify that when os.replace fails, temp file is removed and target is intact."""
        cfg_file = tmp_path / "atomic_target.yaml"
        initial_content = "original_key: original_value\n"
        cfg_file.write_text(initial_content, encoding="utf-8")

        mutator = ConfigMutator(config_path=str(cfg_file))

        with patch.object(Path, "replace", side_effect=OSError("Simulated disk error during replace")):
            success = mutator.save_key(["new_key"], "new_val")
            assert success is False

        # Verify original file untouched
        assert cfg_file.read_text(encoding="utf-8") == initial_content
        # Verify temporary file cleaned up
        assert len(list(tmp_path.glob("*.tmp*"))) == 0


# ===========================================================================
# 4. MetaTuningEngine Facade Robustness & Orchestration Tests
# ===========================================================================

class TestMetaTuningEngineRobustness:
    """End-to-end stress testing of the MetaTuningEngine facade under fault conditions."""

    @pytest.fixture
    def setup_engine(self, tmp_path: Path):
        db = DatabaseManager(str(tmp_path / "engine_test.db"))
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
        return engine, db, cfg, cfg_yaml, tmp_path

    def test_adversarial_prompts_through_facade(self, setup_engine):
        """Verify engine.process handles empty, whitespace, and injection prompts without crashing."""
        engine, db, cfg, cfg_yaml, tmp_path = setup_engine

        assert engine.process("") is None
        assert engine.process("   \n\t  ") is None
        assert engine.process("¿Cómo estás?") is None

        # SQL Injection in rule prompt
        sql_injection = "A partir de ahora ' OR 1=1; DROP TABLE engram_observations; --"
        res = engine.process(sql_injection, context_id="abi")
        assert res is not None
        assert res.action_taken == "rule_saved"

        # Verify database table is intact and observation was safely inserted with parameter binding
        con = db.get_connection()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM engram_observations;")
        assert cur.fetchone()[0] >= 1

    def test_report_builder_failure_does_not_break_clarification_loop(self, setup_engine):
        """Verify that when HTML report creation throws an error, the clarification response succeeds."""
        engine, db, cfg, cfg_yaml, tmp_path = setup_engine

        # Turn 1: trigger clarification
        res1 = engine.process("Haz que el coach sea más inteligente con el loot", context_id="abi")
        assert res1.action_taken == "clarification_needed"
        assert engine.pending_clarification is not None

        # Turn 2: response with report generation throwing an exception
        with patch("abi_coach.application.slices.metatuning.engine.create_html_report", side_effect=OSError("Browser launcher broken")):
            res2 = engine.process("Prioriza el valor por casilla", context_id="abi")
            assert res2 is not None
            assert res2.action_taken == "rule_saved"
            assert res2.report_path is None  # Gracefully degraded to None without crashing
            assert "Prioridad de Loot por Casilla" in res2.spoken_response
            assert engine.pending_clarification is None

    def test_clarification_lifecycle_with_cancellation(self, setup_engine):
        """Verify cancellation during pending clarification properly resets FSM state."""
        engine, db, cfg, cfg_yaml, tmp_path = setup_engine

        # Turn 1: vague request with recognized rule tuning prefix and vagueness trigger
        r1 = engine.process("Sé más pro en combate", context_id="abi")
        assert r1.action_taken == "clarification_needed"
        assert engine.pending_clarification is not None

        # Turn 2: user says "olvídalo"
        r2 = engine.process("olvídalo, cancela todo", context_id="abi")
        assert r2.action_taken == "cancelled"
        assert "cancelé" in r2.spoken_response
        assert engine.pending_clarification is None

    def test_clarification_ttl_expiration_branching(self, setup_engine):
        """Verify clarification state at 59s vs 61s expiration behavior through facade."""
        engine, db, cfg, cfg_yaml, tmp_path = setup_engine

        # Turn 1: Start vague request
        engine.process("Haz que el coach sea más inteligente con el loot", context_id="abi")
        assert engine.pending_clarification is not None

        # Case A: At 59s, clarification response is applied as clarification
        engine.pending_clarification.created_at = time.time() - 59.0
        r_within = engine.process("Prioriza el valor por casilla", context_id="abi")
        assert r_within.action_taken == "rule_saved"
        assert "Prioridad de Loot por Casilla" in r_within.spoken_response
        assert engine.pending_clarification is None

        # Case B: At 61s, clarification has expired, response is processed as a fresh independent prompt
        engine.process("Haz que el coach sea más inteligente con el loot", context_id="abi")
        assert engine.pending_clarification is not None
        engine.pending_clarification.created_at = time.time() - 61.0

        # Fresh non-tuning prompt after expiry should return None (not error or clarification)
        r_expired = engine.process("¿Cuántas balas quedan?", context_id="abi")
        assert r_expired is None
        assert engine.pending_clarification is None

    def test_config_mutation_when_disk_file_missing_or_corrupt(self, setup_engine):
        """Verify _apply_config_update executes cleanly even if disk mutation fails."""
        engine, db, cfg, cfg_yaml, tmp_path = setup_engine

        # Point engine to non-existent config file
        engine.config_mutator.config_path = str(tmp_path / "non_existent.yaml")
        # Changing config still updates runtime in-memory AppConfig safely
        res = engine.process("Configuración global cambia la voz a Salomé")
        assert res.action_taken == "config_updated"
        assert cfg.speaker.voice == "es-CO-SalomeNeural"
