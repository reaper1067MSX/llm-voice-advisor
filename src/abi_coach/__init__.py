"""LLM Voice Advisor & Tactical Copilot (ABI Coach).

A real-time voice gaming copilot with local GPU Whisper STT, Natural Edge-TTS,
multimodal LLM inference, Clean Architecture + Hexagonal + Vertical Slices + Result Pattern.

Uses PEP 562 lazy module attribute loading (__getattr__) so importing lightweight
submodules (e.g. abi_coach.domain, abi_coach.infrastructure.config) does not eagerly load
heavy hardware dependencies (faster_whisper, sounddevice, edge_tts, mss).
"""

import importlib
from typing import Any, Dict, Tuple

__version__ = "0.2.2"

_LAZY_IMPORTS: Dict[str, Tuple[str, str]] = {
    # Domain Layer (DDD Core & Result Pattern)
    "Result": ("abi_coach.domain", "Result"),
    "Success": ("abi_coach.domain", "Success"),
    "Failure": ("abi_coach.domain", "Failure"),
    "ok": ("abi_coach.domain", "ok"),
    "fail": ("abi_coach.domain", "fail"),
    "DomainError": ("abi_coach.domain", "DomainError"),
    "EntityNotFoundError": ("abi_coach.domain", "EntityNotFoundError"),
    "TopicKey": ("abi_coach.domain", "TopicKey"),
    "ArmorTier": ("abi_coach.domain", "ArmorTier"),
    "ConfidenceScore": ("abi_coach.domain", "ConfidenceScore"),
    "TokenUsage": ("abi_coach.domain", "TokenUsage"),
    "GameContext": ("abi_coach.domain", "GameContext"),
    "PlayerMemory": ("abi_coach.domain", "PlayerMemory"),
    "TacticalFact": ("abi_coach.domain", "TacticalFact"),
    "LLMProviderPort": ("abi_coach.domain", "LLMProviderPort"),
    "LLMResponseDTO": ("abi_coach.domain", "LLMResponseDTO"),
    # Application Layer (Vertical Slices & Middlewares)
    "ExecutionPipeline": ("abi_coach.application", "ExecutionPipeline"),
    "ExceptionHandlingMiddleware": ("abi_coach.application", "ExceptionHandlingMiddleware"),
    "LoggingMiddleware": ("abi_coach.application", "LoggingMiddleware"),
    "TacticalAdviceHandler": ("abi_coach.application", "TacticalAdviceHandler"),
    "AskTacticalAdviceCommand": ("abi_coach.application", "AskTacticalAdviceCommand"),
    "TacticalAdviceDTO": ("abi_coach.application", "TacticalAdviceDTO"),
    "ContextSwitchHandler": ("abi_coach.application", "ContextSwitchHandler"),
    "CompanionMemoryHandler": ("abi_coach.application", "CompanionMemoryHandler"),
    "TacticalRagHandler": ("abi_coach.application", "TacticalRagHandler"),
    "MetaTuningHandler": ("abi_coach.application", "MetaTuningHandler"),
    # Infrastructure Layer (Hexagonal Adapters & Config)
    "AppConfig": ("abi_coach.infrastructure.config.settings", "AppConfig"),
    "load_config": ("abi_coach.infrastructure.config.settings", "load_config"),
    "create_llm_adapter": ("abi_coach.infrastructure.adapters.llm.factory", "create_llm_adapter"),
    "GeminiAdapter": ("abi_coach.infrastructure.adapters.llm.gemini_adapter", "GeminiAdapter"),
    "NvidiaNimAdapter": ("abi_coach.infrastructure.adapters.llm.nvidia_adapter", "NvidiaNimAdapter"),
    "DatabaseManager": ("abi_coach.infrastructure.adapters.storage.sqlite_manager", "DatabaseManager"),
    "MindCacheLRU": ("abi_coach.infrastructure.adapters.storage.cache", "MindCacheLRU"),
    "SqliteKnowledgeRepository": (
        "abi_coach.infrastructure.adapters.storage.sqlite_knowledge_repo",
        "SqliteKnowledgeRepository",
    ),
    "SqliteMemoryRepository": (
        "abi_coach.infrastructure.adapters.storage.sqlite_memory_repo",
        "SqliteMemoryRepository",
    ),
    "FasterWhisperAudioInputAdapter": (
        "abi_coach.infrastructure.adapters.audio.faster_whisper_adapter",
        "FasterWhisperAudioInputAdapter",
    ),
    "EdgeTtsAudioOutputAdapter": (
        "abi_coach.infrastructure.adapters.audio.faster_whisper_adapter",
        "EdgeTtsAudioOutputAdapter",
    ),
    "WindowsScreenCaptureAdapter": (
        "abi_coach.infrastructure.adapters.vision.windows_capture_adapter",
        "WindowsScreenCaptureAdapter",
    ),
    "BrowserDisplayAdapter": (
        "abi_coach.infrastructure.adapters.reporting.browser_display_adapter",
        "BrowserDisplayAdapter",
    ),
    "TacticalReportBuilder": (
        "abi_coach.infrastructure.adapters.reporting.browser_display_adapter",
        "TacticalReportBuilder",
    ),
    # Presentation Layer (Driving Adapters)
    "main": ("abi_coach.presentation.cli.cli_runner", "main"),
    "run_interactive_loop": ("abi_coach.presentation.voice.ptt_loop_runner", "run_interactive_loop"),
    "should_inspect_screen": ("abi_coach.presentation.voice.ptt_loop_runner", "should_inspect_screen"),
    "BANNER": ("abi_coach.presentation.voice.ptt_loop_runner", "BANNER"),
    # Canonical Adapters, Orchestration & Vertical Slices
    "AudioListener": ("abi_coach.infrastructure.adapters.audio.listener", "AudioListener"),
    "Speaker": ("abi_coach.infrastructure.adapters.audio.speaker", "Speaker"),
    "capture_screen": ("abi_coach.infrastructure.adapters.vision.capture", "capture_screen"),
    "LLMProvider": ("abi_coach.infrastructure.adapters.llm.base", "LLMProvider"),
    "create_llm_provider": ("abi_coach.infrastructure.adapters.llm.factory", "create_llm_provider"),
    "Brain": ("abi_coach.application.orchestration.brain", "Brain"),
    "CoachResponse": ("abi_coach.application.orchestration.brain", "CoachResponse"),
    "Turn": ("abi_coach.application.orchestration.brain", "Turn"),
    "load_preset": ("abi_coach.application.orchestration.brain", "load_preset"),
    "ArchetypeManager": ("abi_coach.application.slices.archetypes", "ArchetypeManager"),
    "ArchetypeScaffolder": ("abi_coach.application.slices.archetypes", "ArchetypeScaffolder"),
    "DynamicEntity": ("abi_coach.application.slices.archetypes", "DynamicEntity"),
    "TopicContext": ("abi_coach.application.slices.archetypes", "TopicContext"),
    "KnowledgeItem": ("abi_coach.application.slices.tactical_rag", "KnowledgeItem"),
    "KnowledgeRAG": ("abi_coach.application.slices.tactical_rag", "KnowledgeRAG"),
    "KnowledgeReconciler": ("abi_coach.application.slices.tactical_rag", "KnowledgeReconciler"),
    "ReconciliationDiff": ("abi_coach.application.slices.tactical_rag", "ReconciliationDiff"),
    "CompanionMemory": ("abi_coach.application.slices.companion_memory", "CompanionMemory"),
    "MemoryItem": ("abi_coach.application.slices.companion_memory", "MemoryItem"),
    "MetaTuningEngine": ("abi_coach.application.slices.metatuning", "MetaTuningEngine"),
    "MetaTuningResult": ("abi_coach.application.slices.metatuning", "MetaTuningResult"),
    "ClarificationState": ("abi_coach.application.slices.metatuning", "ClarificationState"),
    "create_html_report": ("abi_coach.application.slices.reporting", "create_html_report"),
    "create_tactical_dashboard": ("abi_coach.application.slices.reporting", "create_tactical_dashboard"),
}

__all__ = ["__version__", *_LAZY_IMPORTS.keys()]


def __getattr__(name: str) -> Any:
    """PEP 562 lazy attribute loader for abi_coach root package."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return list(__all__)

