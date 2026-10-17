"""Configuration loader and schema definition (Infrastructure Config)."""

from abi_coach.infrastructure.config.settings import (
    AppConfig,
    CaptureConfig,
    CaptureRegion,
    GeminiConfig,
    HistoryConfig,
    ListenerConfig,
    LLMConfig,
    MoonshotConfig,
    NvidiaConfig,
    ReportConfig,
    ResilienceConfig,
    SpeakerConfig,
    load_config,
)

ReportsConfig = ReportConfig

__all__ = [
    "AppConfig",
    "GeminiConfig",
    "NvidiaConfig",
    "MoonshotConfig",
    "ResilienceConfig",
    "LLMConfig",
    "CaptureConfig",
    "CaptureRegion",
    "ListenerConfig",
    "SpeakerConfig",
    "ReportConfig",
    "ReportsConfig",
    "HistoryConfig",
    "load_config",
]
