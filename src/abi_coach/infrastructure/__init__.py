"""Infrastructure Layer: Configuration and Hexagonal Adapters (PEP 562 lazy exports)."""

import importlib
from typing import Any, Dict, Tuple

_LAZY_IMPORTS: Dict[str, Tuple[str, str]] = {
    "AppConfig": ("abi_coach.infrastructure.config", "AppConfig"),
    "load_config": ("abi_coach.infrastructure.config", "load_config"),
    "GeminiAdapter": ("abi_coach.infrastructure.adapters", "GeminiAdapter"),
    "GeminiProvider": ("abi_coach.infrastructure.adapters", "GeminiProvider"),
    "LLMProvider": ("abi_coach.infrastructure.adapters", "LLMProvider"),
    "NvidiaNIMProvider": ("abi_coach.infrastructure.adapters", "NvidiaNIMProvider"),
    "NvidiaNimAdapter": ("abi_coach.infrastructure.adapters", "NvidiaNimAdapter"),
    "ProviderResponse": ("abi_coach.infrastructure.adapters", "ProviderResponse"),
    "create_llm_adapter": ("abi_coach.infrastructure.adapters", "create_llm_adapter"),
    "create_llm_provider": ("abi_coach.infrastructure.adapters", "create_llm_provider"),
    "CacheEntry": ("abi_coach.infrastructure.adapters", "CacheEntry"),
    "DatabaseManager": ("abi_coach.infrastructure.adapters", "DatabaseManager"),
    "MindCacheLRU": ("abi_coach.infrastructure.adapters", "MindCacheLRU"),
    "SqliteKnowledgeRepository": ("abi_coach.infrastructure.adapters", "SqliteKnowledgeRepository"),
    "SqliteMemoryRepository": ("abi_coach.infrastructure.adapters", "SqliteMemoryRepository"),
    "AudioListener": ("abi_coach.infrastructure.adapters", "AudioListener"),
    "FasterWhisperAudioInputAdapter": ("abi_coach.infrastructure.adapters", "FasterWhisperAudioInputAdapter"),
    "EdgeTtsAudioOutputAdapter": ("abi_coach.infrastructure.adapters", "EdgeTtsAudioOutputAdapter"),
    "Speaker": ("abi_coach.infrastructure.adapters", "Speaker"),
    "ProcessedCapture": ("abi_coach.infrastructure.adapters", "ProcessedCapture"),
    "WindowsScreenCaptureAdapter": ("abi_coach.infrastructure.adapters", "WindowsScreenCaptureAdapter"),
    "capture_screen": ("abi_coach.infrastructure.adapters", "capture_screen"),
    "BrowserDisplayAdapter": ("abi_coach.infrastructure.adapters", "BrowserDisplayAdapter"),
    "TacticalReportBuilder": ("abi_coach.infrastructure.adapters", "TacticalReportBuilder"),
}

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


