"""Unit tests for Pure Domain Layer and Result Pattern."""

import pytest

from abi_coach.domain.common.errors import (
    AmbiguousInstructionError,
    DomainError,
    EntityNotFoundError,
    ProviderError,
    SystemUnexpectedError,
    ValidationError,
)
from abi_coach.domain.common.result import Failure, Result, Success, fail, ok
from abi_coach.domain.common.value_objects import ArmorTier, ConfidenceScore, TokenUsage, TopicKey
from abi_coach.domain.entities.game_context import GameContext
from abi_coach.domain.entities.player_memory import PlayerMemory


def test_result_success_railway():
    res = ok(10)
    assert res.is_ok()
    assert not res.is_err()
    assert res.unwrap() == 10
    assert res.unwrap_or(0) == 10

    # map
    res2 = res.map(lambda x: x * 2)
    assert isinstance(res2, Success)
    assert res2.value == 20

    # bind to another success
    res3 = res2.bind(lambda x: ok(f"Value: {x}"))
    assert res3.unwrap() == "Value: 20"

    # bind to failure
    err = ValidationError(code="ERR_VAL", message="Too high")
    res4 = res2.bind(lambda x: fail(err))
    assert res4.is_err()
    assert res4.error == err


def test_result_failure_railway():
    err = EntityNotFoundError(code="NOT_FOUND", message="Weapon missing", entity_id="m4a1")
    res = fail(err)

    assert not res.is_ok()
    assert res.is_err()
    assert res.error == err
    assert res.unwrap_or("fallback") == "fallback"

    with pytest.raises(Exception):
        res.unwrap()

    # map preserves failure without calling function
    call_log = []
    res2 = res.map(lambda x: call_log.append(x))
    assert res2.is_err()
    assert len(call_log) == 0

    # bind preserves failure
    res3 = res.bind(lambda x: ok("Should not happen"))
    assert res3.is_err()
    assert res3.error == err


def test_topic_key_value_object():
    tk = TopicKey.create(game="abi", topic="balistica", facet="m80")
    assert str(tk) == "abi/balistica/m80"
    assert tk.game == "abi"
    assert tk.topic == "balistica"
    assert tk.facet == "m80"

    # Empty check
    with pytest.raises(ValueError):
        TopicKey("")

    # Invalid characters check
    with pytest.raises(ValueError):
        TopicKey("game with spaces/bad!key")


def test_armor_tier_value_object():
    tier4 = ArmorTier(4)
    assert tier4.tier == 4
    assert tier4.label == "Tier 4"
    assert tier4.color_class == "tier4"

    tier6 = ArmorTier(6)
    assert tier6.color_class == "tier6"

    with pytest.raises(ValueError):
        ArmorTier(0)

    with pytest.raises(ValueError):
        ArmorTier(7)


def test_confidence_score_and_token_usage():
    c = ConfidenceScore(1.5)
    assert c.score == 1.0
    assert c.is_reliable()

    c_low = ConfidenceScore(-0.2)
    assert c_low.score == 0.0
    assert not c_low.is_reliable()

    usage = TokenUsage(input_tokens=150, output_tokens=50)
    assert usage.total_tokens == 200


def test_game_context_aggregate():
    ctx = GameContext(context_id="abi", display_name="Arena Breakout: Infinite")
    assert not ctx.is_active
    ctx.activate()
    assert ctx.is_active

    ctx.add_rule("Descartar balas de tier bajo")
    ctx.add_rule("Descartar balas de tier bajo")  # deduplicated
    assert len(ctx.rules) == 1
    assert ctx.rules[0] == "Descartar balas de tier bajo"


def test_player_memory_entity():
    tk = TopicKey("abi/economy/loot_priority")
    mem = PlayerMemory(
        topic_key=tk,
        title="Prioridad Loot",
        content="Priorizar oro",
        pinned=False,
    )
    assert mem.access_count == 0
    mem.mark_accessed()
    assert mem.access_count == 1
    assert not mem.pinned

    mem.pin()
    assert mem.pinned
    mem.unpin()
    assert not mem.pinned


def test_domain_error_spoken_messages():
    err = EntityNotFoundError(code="E1", message="Technical missing msg", entity_id="M80")
    assert "M80" in err.get_spoken_message()

    amb = AmbiguousInstructionError(
        code="AMBIGUOUS",
        message="Too vague",
        clarification_question="¿Deseas priorizar penetración o daño?",
    )
    assert amb.get_spoken_message() == "¿Deseas priorizar penetración o daño?"

    sys_err = SystemUnexpectedError(code="SYS_ERR", message="Crash", technical_detail="Out of VRAM")
    assert "fallo temporal" in sys_err.get_spoken_message()
