"""Infrastructure Adapters package."""

from abi_coach.infrastructure.adapters.audio import EdgeTtsAudioOutputAdapter, FasterWhisperAudioInputAdapter
from abi_coach.infrastructure.adapters.llm import GeminiAdapter, NvidiaNimAdapter, create_llm_adapter
from abi_coach.infrastructure.adapters.reporting import BrowserDisplayAdapter, TacticalReportBuilder
from abi_coach.infrastructure.adapters.storage import (
    DatabaseManager,
    MindCacheLRU,
    SqliteKnowledgeRepository,
    SqliteMemoryRepository,
)
from abi_coach.infrastructure.adapters.vision import WindowsScreenCaptureAdapter

__all__ = [
    # LLM
    "GeminiAdapter",
    "NvidiaNimAdapter",
    "create_llm_adapter",
    # Storage
    "DatabaseManager",
    "MindCacheLRU",
    "SqliteKnowledgeRepository",
    "SqliteMemoryRepository",
    # Audio
    "FasterWhisperAudioInputAdapter",
    "EdgeTtsAudioOutputAdapter",
    # Vision
    "WindowsScreenCaptureAdapter",
    # Reporting
    "BrowserDisplayAdapter",
    "TacticalReportBuilder",
]
