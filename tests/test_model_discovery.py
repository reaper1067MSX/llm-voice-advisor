"""Unit tests for Model Discovery Service, Moonshot Quota Failover, and Factory Injection."""

from unittest.mock import MagicMock, patch

import httpx

from abi_coach.application.services.model_discovery import (
    DiscoveredModelsReport,
    ModelDiscoveryService,
)
from abi_coach.domain.common.errors import ProviderError
from abi_coach.domain.common.result import fail, ok
from abi_coach.domain.ports.llm_port import LLMResponseDTO
from abi_coach.infrastructure.adapters.llm.factory import create_llm_adapter
from abi_coach.infrastructure.adapters.llm.moonshot_adapter import MoonshotAdapter
from abi_coach.infrastructure.adapters.llm.resilient_orchestrator import (
    ResilientLLMOrchestrator,
)
from abi_coach.infrastructure.config.settings import (
    AppConfig,
    GeminiConfig,
    MoonshotConfig,
    NvidiaConfig,
    ResilienceConfig,
    load_config,
)


class DummyModel:
    """Mock Google GenAI Model representation."""

    def __init__(self, name: str, supported_actions=None):
        self.name = name
        self.supported_actions = supported_actions


# ==============================================================================
# 1. DiscoveredModelsReport Unit Tests
# ==============================================================================


def test_discovered_models_report_helpers():
    """Verify helper methods for selecting best model and building fallback cascade."""
    report = DiscoveredModelsReport(
        gemini_models=["gemini-2.5-flash", "gemini-3.1-flash-lite", "gemini-3.5-flash"],
        moonshot_available=True,
        nvidia_available=True,
        moonshot_base_url="https://api.moonshot.ai/v1",
        moonshot_model="kimi-k2.6",
    )

    assert report.has_any_provider() is True
    assert report.has_gemini() is True
    assert report.best_gemini_model() == "gemini-3.5-flash"

    cascade = report.build_fallback_cascade(include_nvidia=True)
    assert "gemini-lite" in cascade
    assert "moonshot" in cascade
    assert "nvidia" in cascade

    report_dict = report.to_dict()
    assert report_dict["moonshot_available"] is True
    assert report_dict["nvidia_available"] is True
    assert report_dict["moonshot_model"] == "kimi-k2.6"


def test_discovered_models_report_fallback_when_empty():
    """Verify fallback behavior when report contains no discovered models."""
    empty_report = DiscoveredModelsReport()
    assert empty_report.has_any_provider() is False
    assert empty_report.has_gemini() is False
    assert empty_report.best_gemini_model(fallback="custom-gemini") == "custom-gemini"
    assert empty_report.build_fallback_cascade() == []


# ==============================================================================
# 2. ModelDiscoveryService — Gemini Discovery Tests
# ==============================================================================


def test_gemini_discovery_filtering_and_priority(monkeypatch):
    """Verify that only generative Gemini models are discovered and sorted by priority."""
    mock_models = [
        DummyModel("models/gemini-embedding-001", supported_actions=["embedContent"]),
        DummyModel("models/gemini-2.5-flash", supported_actions=["generateContent"]),
        DummyModel("models/text-bison-001", supported_actions=["generateContent"]),
        DummyModel("models/gemini-3.5-flash", supported_actions=["generateContent"]),
        DummyModel("models/gemini-3.1-flash-lite", supported_actions=["generateContent"]),
        DummyModel("models/gemini-3.8-live", supported_actions=["bidiGenerateContent"]),
    ]

    mock_client = MagicMock()
    mock_client.models.list.return_value = mock_models

    with patch("google.genai.Client", return_value=mock_client):
        service = ModelDiscoveryService(gemini_api_key="test-gemini-key")
        discovered = service.discover_gemini_models()

        assert "gemini-embedding-001" not in discovered
        assert "text-bison-001" not in discovered
        assert "gemini-3.8-live" not in discovered
        assert "gemini-3.5-flash" in discovered
        assert "gemini-3.1-flash-lite" in discovered
        assert "gemini-2.5-flash" in discovered

        # Verification of priority order: 3.5-flash > 3.1-flash-lite > 2.5-flash
        assert discovered[0] == "gemini-3.5-flash"
        assert discovered[1] == "gemini-3.1-flash-lite"
        assert discovered[2] == "gemini-2.5-flash"


def test_gemini_discovery_empty_or_failing_key():
    """Verify graceful handling when key is missing or GenAI SDK encounters errors."""
    service_no_key = ModelDiscoveryService(gemini_api_key="")
    assert service_no_key.discover_gemini_models() == []

    with patch("google.genai.Client", side_effect=ValueError("Invalid key")):
        service_failing = ModelDiscoveryService(gemini_api_key="bad-key")
        assert service_failing.discover_gemini_models() == []


# ==============================================================================
# 3. ModelDiscoveryService — Moonshot Connectivity Tests
# ==============================================================================


def test_moonshot_connectivity_primary_success():
    """Verify Moonshot connectivity check against primary international endpoint."""
    service = ModelDiscoveryService(moonshot_api_key="test-msh-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "kimi-k2.6", "owned_by": "moonshot"},
            {"id": "kimi-k2.7-code", "owned_by": "moonshot"},
        ]
    }

    with patch.object(httpx.Client, "get", return_value=mock_resp):
        ok_flag, base_url, models = service.check_moonshot_connectivity()
        assert ok_flag is True
        assert base_url == "https://api.moonshot.ai/v1"
        assert "kimi-k2.6" in models


def test_moonshot_connectivity_fallback_to_china_endpoint():
    """Verify fallback to mainland China endpoint if international domain fails."""
    service = ModelDiscoveryService(moonshot_api_key="test-msh-key")

    def side_effect(url, headers=None):
        if "api.moonshot.ai" in url:
            raise httpx.ConnectError("Network timeout on .ai domain")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"id": "kimi-k2.6"}]}
        return mock_resp

    with patch.object(httpx.Client, "get", side_effect=side_effect):
        ok_flag, base_url, models = service.check_moonshot_connectivity()
        assert ok_flag is True
        assert base_url == "https://api.moonshot.cn/v1"
        assert "kimi-k2.6" in models


def test_moonshot_connectivity_missing_key_and_total_failure():
    """Verify returns False when key is absent or all endpoints fail."""
    service_no_key = ModelDiscoveryService(moonshot_api_key="")
    assert service_no_key.check_moonshot_connectivity() == (
        False,
        "https://api.moonshot.ai/v1",
        [],
    )

    service = ModelDiscoveryService(moonshot_api_key="test-key")
    with patch.object(
        httpx.Client, "get", side_effect=httpx.ConnectError("Connection refused")
    ):
        ok_flag, _, models = service.check_moonshot_connectivity()
        assert ok_flag is False
        assert models == []


# ==============================================================================
# 4. MoonshotAdapter Quota & Rate Limit Error Handling Tests
# ==============================================================================


def test_moonshot_adapter_429_quota_error():
    """Verify MoonshotAdapter maps HTTP 429 quota exhaustion to MOONSHOT_QUOTA_ERROR."""
    adapter = MoonshotAdapter(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Account suspended due to insufficient balance"
    mock_resp.json.return_value = {
        "error": {
            "type": "exceeded_current_quota_error",
            "message": "Your account is suspended due to insufficient balance",
        }
    }

    with patch.object(adapter._client, "post", return_value=mock_resp):
        res = adapter.generate(prompt="Hola", system_instruction="Act as coach")
        assert res.is_err()
        err = res.error
        assert isinstance(err, ProviderError)
        assert err.code == "MOONSHOT_QUOTA_ERROR"
        assert err.is_transient is True
        assert err.retryable is False
        assert "insufficient balance" in err.message


def test_moonshot_adapter_429_rate_limit_error():
    """Verify MoonshotAdapter maps HTTP 429 rate limit to MOONSHOT_RATE_LIMIT."""
    adapter = MoonshotAdapter(api_key="test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "RPM rate limit reached"
    mock_resp.json.return_value = {
        "error": {
            "type": "rate_limit_reached_error",
            "message": "Requests per minute limit exceeded",
        }
    }

    with patch.object(adapter._client, "post", return_value=mock_resp):
        res = adapter.generate(prompt="Hola", system_instruction="Act as coach")
        assert res.is_err()
        err = res.error
        assert isinstance(err, ProviderError)
        assert err.code == "MOONSHOT_RATE_LIMIT"
        assert err.is_transient is True
        assert err.retryable is True


# ==============================================================================
# 5. Resilient Failover Cascade on Moonshot Quota Error
# ==============================================================================


def test_resilient_cascade_failover_on_moonshot_quota_error():
    """Verify that ResilientLLMOrchestrator smoothly rotates on Moonshot 429 quota error."""
    # Primary (Gemini) fails with 503
    mock_primary = MagicMock()
    mock_primary.generate.return_value = fail(
        ProviderError(
            code="GEMINI_503",
            message="Gemini overloaded",
            provider_name="gemini-3.5-flash",
        )
    )

    # Fallback 1 (Moonshot) fails with 429 quota error
    mock_moonshot = MagicMock()
    mock_moonshot.generate.return_value = fail(
        ProviderError(
            code="MOONSHOT_QUOTA_ERROR",
            message="Cuota agotada en Kimi",
            provider_name="moonshot",
            is_transient=True,
            retryable=False,
        )
    )

    # Fallback 2 (NVIDIA NIM) succeeds
    mock_nvidia = MagicMock()
    mock_nvidia.generate.return_value = ok(
        LLMResponseDTO(
            spoken_text="Respuesta táctica generada por NVIDIA NIM",
            latency_ms=120.0,
            provider_name="nvidia-nim",
        )
    )

    orchestrator = ResilientLLMOrchestrator(
        primary=("gemini-3.5-flash", mock_primary),
        fallbacks=[
            ("kimi-moonshot", mock_moonshot),
            ("nvidia-nim", mock_nvidia),
        ],
        failure_threshold=1,
    )

    res = orchestrator.generate(prompt="Dame tácticas", system_instruction="Coach")
    assert res.is_ok()
    dto = res.unwrap()
    assert dto.spoken_text == "Respuesta táctica generada por NVIDIA NIM"
    assert dto.provider_name == "nvidia-nim"


# ==============================================================================
# 6. Factory Integration with DiscoveredModelsReport
# ==============================================================================


def test_factory_injects_discovered_models():
    """Verify create_llm_adapter incorporates DiscoveredModelsReport into primary and fallbacks."""
    report = DiscoveredModelsReport(
        gemini_models=["gemini-3.5-flash", "gemini-3.1-flash-lite"],
        moonshot_available=True,
        nvidia_available=True,
        moonshot_base_url="https://api.moonshot.ai/v1",
        moonshot_model="kimi-k2.6",
    )

    config = AppConfig(
        gemini=GeminiConfig(api_key="mock-gemini-key"),
        moonshot=MoonshotConfig(api_key="mock-msh-key"),
        nvidia=NvidiaConfig(api_key="mock-nvd-key"),
        resilience=ResilienceConfig(enabled=True),
    )

    adapter = create_llm_adapter(config, discovered_report=report)
    assert isinstance(adapter, ResilientLLMOrchestrator)

    assert adapter.primary_name == "gemini-3.5-flash"
    fallback_names = [name for name, _ in adapter.fallbacks]
    assert "gemini-3.1-flash-lite" in fallback_names
    assert "kimi-moonshot" in fallback_names
    assert "nvidia-nim" in fallback_names


# ==============================================================================
# 7. Settings Configuration Defaults & Loading
# ==============================================================================


def test_settings_moonshot_defaults(tmp_path):
    """Verify Moonshot defaults in settings dataclass and load_config."""
    config = AppConfig()
    assert config.moonshot.model == "kimi-k2.6"
    assert config.moonshot.base_url == "https://api.moonshot.ai/v1"

    # Verify loading from YAML without explicit moonshot block preserves defaults
    test_yaml = tmp_path / "test_config.yaml"
    test_yaml.write_text("gemini:\n  model: gemini-3.5-flash\n", encoding="utf-8")

    loaded = load_config(str(test_yaml))
    assert loaded.moonshot.model == "kimi-k2.6"
    assert loaded.moonshot.base_url == "https://api.moonshot.ai/v1"


def test_model_discovery_full_discover():
    """Verify ModelDiscoveryService.discover runs unified detection across all providers."""
    mock_models = [
        DummyModel("models/gemini-3.5-flash", supported_actions=["generateContent"]),
        DummyModel("models/gemini-3.1-flash-lite", supported_actions=["generateContent"]),
    ]
    mock_client = MagicMock()
    mock_client.models.list.return_value = mock_models

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": [{"id": "kimi-k2.6"}]}

    with (
        patch("google.genai.Client", return_value=mock_client),
        patch.object(httpx.Client, "get", return_value=mock_resp),
    ):
        service = ModelDiscoveryService(
            gemini_api_key="mock-gemini",
            moonshot_api_key="mock-moonshot",
            nvidia_api_key="mock-nvidia",
        )
        report = service.discover()

        assert "gemini-3.5-flash" in report.gemini_models
        assert report.moonshot_available is True
        assert report.nvidia_available is True
        assert report.moonshot_model == "kimi-k2.6"
        assert report.has_any_provider() is True

