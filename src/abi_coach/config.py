"""Backward compatibility shim for abi_coach.config."""

from abi_coach.core.config import (
    AppConfig,
    CaptureConfig,
    CaptureRegion,
    GeminiConfig,
    HistoryConfig,
    LLMConfig,
    ListenerConfig,
    NvidiaConfig,
    ReportConfig,
    SpeakerConfig,
    load_config,
)

__all__ = [
    "AppConfig",
    "CaptureConfig",
    "CaptureRegion",
    "GeminiConfig",
    "HistoryConfig",
    "LLMConfig",
    "ListenerConfig",
    "NvidiaConfig",
    "ReportConfig",
    "SpeakerConfig",
    "load_config",
]
