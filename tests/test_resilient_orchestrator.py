"""Tests for ResilientLLMOrchestrator, CircuitBreaker, MoonshotAdapter, and Mute Toggle."""

import time
from unittest.mock import MagicMock, patch

import pytest

from abi_coach.domain.common.errors import ProviderError
from abi_coach.domain.common.result import fail, ok
from abi_coach.domain.ports.llm_port import LLMProviderPort, LLMResponseDTO
from abi_coach.infrastructure.adapters.audio.listener import AudioListener
from abi_coach.infrastructure.adapters.llm.circuit_breaker import CircuitBreaker, CircuitState
from abi_coach.infrastructure.adapters.llm.moonshot_adapter import MoonshotAdapter
from abi_coach.infrastructure.adapters.llm.resilient_orchestrator import ResilientLLMOrchestrator
from abi_coach.infrastructure.config.settings import ListenerConfig


def test_circuit_breaker_state_transitions():
    """Verify CircuitBreaker moves CLOSED -> OPEN -> HALF_OPEN -> CLOSED properly."""
    breaker = CircuitBreaker(name="test-breaker", failure_threshold=2, recovery_timeout_sec=0.1)

    assert breaker.get_state() == CircuitState.CLOSED
    assert breaker.can_execute() is True
    assert breaker.is_open is False

    # First failure: should remain CLOSED
    breaker.record_failure(Exception("503 error 1"))
    assert breaker.get_state() == CircuitState.CLOSED
    assert breaker.can_execute() is True

    # Second failure (threshold reached): should trip to OPEN
    breaker.record_failure(Exception("503 error 2"))
    assert breaker.get_state() == CircuitState.OPEN
    assert breaker.can_execute() is False
    assert breaker.is_open is True

    # Immediate call while cooldown has not elapsed: still rejected
    assert breaker.can_execute() is False

    # Wait for cooldown recovery timeout (0.1s)
    time.sleep(0.12)

    # First call after timeout: transitions to HALF_OPEN
    assert breaker.can_execute() is True
    assert breaker.get_state() == CircuitState.HALF_OPEN

    # Success in HALF_OPEN: restores circuit to CLOSED
    breaker.record_success()
    assert breaker.get_state() == CircuitState.CLOSED
    assert breaker.failure_count == 0
    assert breaker.can_execute() is True


def test_circuit_breaker_half_open_failure_reopens():
    """Verify failure in HALF_OPEN state immediately re-trips to OPEN."""
    breaker = CircuitBreaker(name="test-breaker", failure_threshold=1, recovery_timeout_sec=0.05)
    breaker.record_failure(Exception("fail"))
    assert breaker.get_state() == CircuitState.OPEN

    time.sleep(0.06)
    assert breaker.can_execute() is True
    assert breaker.get_state() == CircuitState.HALF_OPEN

    # Failure during probe request
    breaker.record_failure(Exception("still failing"))
    assert breaker.get_state() == CircuitState.OPEN
    assert breaker.can_execute() is False


def test_resilient_orchestrator_normal_execution():
    """Verify primary provider is used when healthy."""
    primary_mock = MagicMock(spec=LLMProviderPort)
    primary_mock.generate.return_value = ok(
        LLMResponseDTO(spoken_text="Respuesta de Gemini", latency_ms=150.0, provider_name="gemini")
    )

    fallback_mock = MagicMock(spec=LLMProviderPort)

    orch = ResilientLLMOrchestrator(
        primary=("gemini", primary_mock),
        fallbacks=[("moonshot", fallback_mock)],
        failure_threshold=2,
    )

    res = orch.generate(prompt="Hola", system_instruction="Coach")
    assert res.is_ok()
    dto = res.unwrap()
    assert dto.spoken_text == "Respuesta de Gemini"
    assert primary_mock.generate.call_count == 1
    assert fallback_mock.generate.call_count == 0


def test_resilient_orchestrator_failover_cascade():
    """Verify failover to fallback provider when primary fails with 503."""
    primary_mock = MagicMock(spec=LLMProviderPort)
    primary_mock.generate.return_value = fail(
        ProviderError(
            code="GEMINI_503_OVERLOADED",
            message="Google 503 Service Unavailable",
            provider_name="gemini",
        )
    )

    fallback_mock = MagicMock(spec=LLMProviderPort)
    fallback_mock.generate.return_value = ok(
        LLMResponseDTO(spoken_text="Respuesta de Kimi", latency_ms=210.0, provider_name="moonshot")
    )

    failover_log = []

    def on_failover(failed_name, reason, next_name):
        failover_log.append((failed_name, reason, next_name))

    orch = ResilientLLMOrchestrator(
        primary=("gemini", primary_mock),
        fallbacks=[("moonshot", fallback_mock)],
        failure_threshold=2,
        on_failover=on_failover,
    )

    res = orch.generate(prompt="¿Qué mod farmear en Once Human?", system_instruction="Coach")
    assert res.is_ok()
    dto = res.unwrap()
    assert dto.spoken_text == "Respuesta de Kimi"
    assert dto.provider_name == "moonshot"
    assert primary_mock.generate.call_count == 1
    assert fallback_mock.generate.call_count == 1

    # Verify failover callback was triggered
    assert len(failover_log) == 1
    assert failover_log[0][0] == "gemini"
    assert failover_log[0][2] == "moonshot"


def test_resilient_orchestrator_circuit_open_skips_primary():
    """Verify that when primary circuit is OPEN, it is skipped without calling generate()."""
    primary_mock = MagicMock(spec=LLMProviderPort)
    primary_mock.generate.return_value = fail(
        ProviderError(code="ERR", message="Fail", provider_name="gemini")
    )

    fallback_mock = MagicMock(spec=LLMProviderPort)
    fallback_mock.generate.return_value = ok(
        LLMResponseDTO(spoken_text="Fallback OK", provider_name="moonshot")
    )

    orch = ResilientLLMOrchestrator(
        primary=("gemini", primary_mock),
        fallbacks=[("moonshot", fallback_mock)],
        failure_threshold=1,  # 1 failure trips circuit
        recovery_timeout_sec=10.0,
    )

    # First call: primary fails, fallback succeeds, breaker trips
    orch.generate(prompt="test 1", system_instruction="")
    assert primary_mock.generate.call_count == 1
    assert orch.breakers["gemini"].get_state() == CircuitState.OPEN

    # Second call: primary should NOT be invoked at all (Fail-Fast)
    res2 = orch.generate(prompt="test 2", system_instruction="")
    assert res2.is_ok()
    assert primary_mock.generate.call_count == 1  # count did NOT increase
    assert fallback_mock.generate.call_count == 2


def test_moonshot_adapter_missing_key():
    """Verify MoonshotAdapter fails fast when MOONSHOT_API_KEY is missing."""
    adapter = MoonshotAdapter(api_key="")
    res = adapter.generate(prompt="test", system_instruction="system")
    assert res.is_err()
    assert res.error.code == "MOONSHOT_AUTH_ERROR"


def test_moonshot_adapter_success_http_call(monkeypatch):
    """Verify MoonshotAdapter processes OpenAI-compatible responses via httpx."""
    adapter = MoonshotAdapter(api_key="valid-test-key")

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "choices": [
            {"message": {"content": "Respuesta táctica desde Kimi K2 / Moonshot v1"}}
        ],
        "usage": {"prompt_tokens": 45, "completion_tokens": 15},
    }

    fake_client = MagicMock()
    fake_client.post.return_value = fake_response
    monkeypatch.setattr(adapter, "_client", fake_client)

    res = adapter.generate(prompt="¿Dónde cae el mod Violent?", system_instruction="Once Human")
    assert res.is_ok()
    dto = res.unwrap()
    assert dto.spoken_text == "Respuesta táctica desde Kimi K2 / Moonshot v1"
    assert dto.provider_name == "moonshot"
    assert dto.tokens.input_tokens == 45
    assert dto.tokens.output_tokens == 15


def test_audio_listener_mute_toggle():
    """Verify AudioListener mute controls and acoustic feedback."""
    cfg = ListenerConfig(mute_key="f10")
    listener = AudioListener(config=cfg)

    assert listener.is_muted() is False

    # Toggle to muted
    with patch("abi_coach.infrastructure.adapters.audio.listener.play_beep") as mock_beep:
        is_muted = listener.toggle_mute()
        assert is_muted is True
        assert listener.is_muted() is True
        mock_beep.assert_called_with(500, 70)

    # Toggle back to unmuted
    with patch("abi_coach.infrastructure.adapters.audio.listener.play_beep") as mock_beep:
        is_muted = listener.toggle_mute()
        assert is_muted is False
        assert listener.is_muted() is False
        assert mock_beep.call_count >= 1

    # Explicit mute and unmute
    listener.mute()
    assert listener.is_muted() is True
    listener.mute()  # idempotency check
    assert listener.is_muted() is True

    listener.unmute()
    assert listener.is_muted() is False
    listener.unmute()  # idempotency check
    assert listener.is_muted() is False
