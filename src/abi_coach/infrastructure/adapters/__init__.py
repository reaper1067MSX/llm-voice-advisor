"""Infrastructure Adapters package (PEP 562 lazy exports)."""

import importlib
from typing import Any, Dict, Tuple

_LAZY_IMPORTS: Dict[str, Tuple[str, str]] = {
    # LLM
    "GeminiAdapter": ("abi_coach.infrastructure.adapters.llm", "GeminiAdapter"),
    "GeminiProvider": ("abi_coach.infrastructure.adapters.llm", "GeminiProvider"),
    "LLMProvider": ("abi_coach.infrastructure.adapters.llm", "LLMProvider"),
    "NvidiaNIMProvider": ("abi_coach.infrastructure.adapters.llm", "NvidiaNIMProvider"),
    "NvidiaNimAdapter": ("abi_coach.infrastructure.adapters.llm", "NvidiaNimAdapter"),
    "ProviderResponse": ("abi_coach.infrastructure.adapters.llm", "ProviderResponse"),
    "create_llm_adapter": ("abi_coach.infrastructure.adapters.llm", "create_llm_adapter"),
    "create_llm_provider": ("abi_coach.infrastructure.adapters.llm", "create_llm_provider"),
    # Storage
    "CacheEntry": ("abi_coach.infrastructure.adapters.storage", "CacheEntry"),
    "DatabaseManager": ("abi_coach.infrastructure.adapters.storage", "DatabaseManager"),
    "MindCacheLRU": ("abi_coach.infrastructure.adapters.storage", "MindCacheLRU"),
    "SqliteKnowledgeRepository": ("abi_coach.infrastructure.adapters.storage", "SqliteKnowledgeRepository"),
    "SqliteMemoryRepository": ("abi_coach.infrastructure.adapters.storage", "SqliteMemoryRepository"),
    # Audio
    "AudioListener": ("abi_coach.infrastructure.adapters.audio", "AudioListener"),
    "EdgeTtsAudioOutputAdapter": ("abi_coach.infrastructure.adapters.audio", "EdgeTtsAudioOutputAdapter"),
    "FasterWhisperAudioInputAdapter": ("abi_coach.infrastructure.adapters.audio", "FasterWhisperAudioInputAdapter"),
    "Speaker": ("abi_coach.infrastructure.adapters.audio", "Speaker"),
    # Vision
    "ProcessedCapture": ("abi_coach.infrastructure.adapters.vision", "ProcessedCapture"),
    "WindowsScreenCaptureAdapter": ("abi_coach.infrastructure.adapters.vision", "WindowsScreenCaptureAdapter"),
    "capture_screen": ("abi_coach.infrastructure.adapters.vision", "capture_screen"),
    # Reporting
    "BrowserDisplayAdapter": ("abi_coach.infrastructure.adapters.reporting", "BrowserDisplayAdapter"),
    "TacticalReportBuilder": ("abi_coach.infrastructure.adapters.reporting", "TacticalReportBuilder"),
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


