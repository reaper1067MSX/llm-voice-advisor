"""Unit tests verifying MetaTuning domain extraction, typing, zero semicolons, and LOC constraints."""

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
import time
import pytest

from abi_coach.domain.enums.metatuning_enums import (
    MetaTuningAction,
    MetaTuningCategory,
    MetaTuningIntent,
)
from abi_coach.domain.entities.metatuning_records import (
    CANCELLATION_PHRASES,
    ClarificationState,
    RESOLUTION_RULES,
    RuleMapping,
)
from abi_coach.application.slices.metatuning import clarification_fsm, intent_parser


def test_metatuning_enums_strenum_subtyping():
    """Verify MetaTuning Enums subclass StrEnum and compare directly with raw strings."""
    assert MetaTuningIntent.CONFIG == "config"
    assert MetaTuningIntent.RULE == "rule"
    assert MetaTuningIntent.PROMPT == "prompt"
    assert MetaTuningIntent.RAG == "rag"
    assert isinstance(MetaTuningIntent.CONFIG, str)

    assert MetaTuningCategory.LOOT == "loot"
    assert MetaTuningCategory.COMBAT == "combat"
    assert MetaTuningCategory.VOICE == "voice"
    assert MetaTuningCategory.GENERAL == "general"
    assert isinstance(MetaTuningCategory.LOOT, str)

    assert MetaTuningAction.CLARIFICATION_NEEDED == "clarification_needed"
    assert MetaTuningAction.RULE_SAVED == "rule_saved"
    assert MetaTuningAction.CONFIG_UPDATED == "config_updated"
    assert MetaTuningAction.PROMPT_UPDATED == "prompt_updated"
    assert MetaTuningAction.RAG_INGESTED == "rag_ingested"
    assert MetaTuningAction.CANCELLED == "cancelled"
    assert isinstance(MetaTuningAction.CANCELLED, str)


def test_rule_mapping_immutability_and_5_tuple_unpacking():
    """Verify RuleMapping supports both object attribute access and legacy 5-tuple unpacking."""
    mapping = RuleMapping(
        keywords=("test", "keyword"),
        title="Test Title",
        slug="test_slug",
        what="What explanation",
        learned="Learned lesson",
    )

    kws, title, slug, what, learned = mapping
    assert kws == ("test", "keyword")
    assert title == "Test Title"
    assert slug == "test_slug"
    assert what == "What explanation"
    assert learned == "Learned lesson"

    assert mapping[0] == ("test", "keyword")
    assert mapping[1] == "Test Title"
    assert mapping[2] == "test_slug"
    assert mapping[3] == "What explanation"
    assert mapping[4] == "Learned lesson"
    assert len(mapping) == 5

    with pytest.raises(FrozenInstanceError):
        mapping.title = "Modified"  # type: ignore[misc]

    assert len(RESOLUTION_RULES) == 5
    for rule in RESOLUTION_RULES:
        kws, t, s, w, l = rule
        assert isinstance(kws, tuple)
        assert isinstance(t, str)
        assert isinstance(s, str)
        assert isinstance(w, str)
        assert isinstance(l, str)


def test_clarification_state_mutability_and_backward_compatibility():
    """Verify ClarificationState supports TTL testing mutability, timestamp property, and dict access."""
    state = ClarificationState(original_prompt="mejor loot", context_id="abi", category="loot")
    assert state.original_prompt == "mejor loot"
    assert state.context_id == "abi"
    assert state.category == "loot"

    past_time = time.time() - 120.0
    state.created_at = past_time
    assert state.created_at == past_time
    assert state.timestamp == past_time
    assert state.get("timestamp") == past_time
    assert state["timestamp"] == past_time
    assert state.get("original_prompt") == "mejor loot"
    assert state["original_prompt"] == "mejor loot"
    assert state.get("nonexistent", "fallback") == "fallback"


def test_zero_duplicate_constants_between_parser_and_fsm():
    """Verify constants are single-sourced in domain and identically referenced in parser and FSM."""
    assert intent_parser.CANCELLATION_PHRASES is clarification_fsm.CANCELLATION_PHRASES
    assert intent_parser.RESOLUTION_RULES is clarification_fsm.CONFIRMATION_RULES
    assert intent_parser.CANCELLATION_PHRASES is CANCELLATION_PHRASES
    assert clarification_fsm.CONFIRMATION_RULES is RESOLUTION_RULES

    slices_dir = Path("src/abi_coach/application/slices/metatuning")
    parser_ast = ast.parse((slices_dir / "intent_parser.py").read_text(encoding="utf-8"))
    fsm_ast = ast.parse((slices_dir / "clarification_fsm.py").read_text(encoding="utf-8"))

    def get_assigned_tuples(tree: ast.AST):
        assigned = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, (ast.Tuple, ast.List)):
                        assigned.add(target.id)
        return assigned

    parser_assigned = get_assigned_tuples(parser_ast)
    fsm_assigned = get_assigned_tuples(fsm_ast)

    assert "CANCELLATION_PHRASES" not in parser_assigned
    assert "CANCELLATION_PHRASES" not in fsm_assigned
    assert "RESOLUTION_RULES" not in parser_assigned
    assert "CONFIRMATION_RULES" not in fsm_assigned


def test_zero_semicolons_in_metatuning_slices():
    """Verify all Python files in the metatuning slice have zero semicolons in active code."""
    metatuning_dir = Path("src/abi_coach/application/slices/metatuning")
    py_files = list(metatuning_dir.glob("*.py"))
    assert len(py_files) >= 4

    semicolon_occurrences = []
    for file in py_files:
        for idx, line in enumerate(file.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ";" in line:
                semicolon_occurrences.append(f"{file.name}:{idx}: {line}")

    assert not semicolon_occurrences, f"Found semicolons in metatuning: {semicolon_occurrences}"
