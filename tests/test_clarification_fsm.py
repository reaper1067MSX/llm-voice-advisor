"""Focused unit tests for ClarificationFSM."""

import threading
import time
import pytest

from abi_coach.application.slices.metatuning.clarification_fsm import ClarificationFSM


def test_clarification_fsm_lifecycle_and_ttl():
    """Verify ClarificationFSM handles transitions, 60s TTL, and cancellation phrases."""
    fsm = ClarificationFSM(ttl_sec=60.0)
    assert fsm.has_pending is False
    assert fsm.pending is None

    state = fsm.start("Haz que el coach sea mejor con el loot", context_id="abi", category="loot")
    assert fsm.has_pending is True
    assert state.category == "loot"
    assert state.timestamp == state.created_at
    assert state.get("timestamp") == state.created_at
    assert state["category"] == "loot"

    assert fsm.is_cancellation("cancela") is True
    assert fsm.is_cancellation("olvídalo") is True
    assert fsm.is_cancellation("no importa") is True
    assert fsm.is_cancellation("sí, continúa") is False

    assert fsm.is_expired() is False
    state.created_at = time.time() - 65.0
    assert fsm.is_expired() is True

    assert fsm.is_expired(auto_reset=True) is True
    assert fsm.has_pending is False
    assert fsm.pending is None

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
