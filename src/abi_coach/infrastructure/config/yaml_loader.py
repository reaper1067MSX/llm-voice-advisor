"""Configuration loader and schema definition (Infrastructure Config)."""

from abi_coach.core.config import (
    AppConfig,
    CaptureConfig,
    CaptureRegion,
    GeminiConfig,
    HistoryConfig,
    ListenerConfig,
    LLMConfig,
    NvidiaConfig,
    ReportConfig,
    SpeakerConfig,
    load_config,
)

ReportsConfig = ReportConfig

__all__ = [
    "AppConfig",
    "GeminiConfig",
    "NvidiaConfig",
    "LLMConfig",
    "CaptureConfig",
    "CaptureRegion",
    "ListenerConfig",
    "SpeakerConfig",
    "ReportsConfig",
    "HistoryConfig",
    "load_config",
]
