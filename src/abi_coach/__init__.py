"""LLM Voice Advisor & Tactical Copilot (ABI Coach).

A real-time voice gaming copilot with local GPU Whisper STT, Natural Edge-TTS,
multimodal LLM inference, Clean Architecture + Hexagonal + Vertical Slices + Result Pattern.
"""

# Domain Layer (DDD Core & Result Pattern)
from abi_coach.domain import (
    ArmorTier,
    ConfidenceScore,
    DomainError,
    EntityNotFoundError,
    Failure,
    GameContext,
    LLMProviderPort,
    LLMResponseDTO,
    PlayerMemory,
    Result,
    Success,
    TacticalFact,
    TokenUsage,
    TopicKey,
    fail,
    ok,
)

# Application Layer (Vertical Slices & Middlewares)
from abi_coach.application import (
    AskTacticalAdviceCommand,
    CompanionMemoryHandler,
    ContextSwitchHandler,
    ExceptionHandlingMiddleware,
    ExecutionPipeline,
    LoggingMiddleware,
    MetaTuningHandler,
    TacticalAdviceDTO,
    TacticalAdviceHandler,
    TacticalRagHandler,
)

# Infrastructure Layer (Hexagonal Adapters & Config)
from abi_coach.infrastructure import (
    AppConfig,
    BrowserDisplayAdapter,
    DatabaseManager,
    EdgeTtsAudioOutputAdapter,
    FasterWhisperAudioInputAdapter,
    GeminiAdapter,
    MindCacheLRU,
    NvidiaNimAdapter,
    SqliteKnowledgeRepository,
    SqliteMemoryRepository,
    TacticalReportBuilder,
    WindowsScreenCaptureAdapter,
    create_llm_adapter,
    load_config,
)

# Presentation Layer (Driving Adapters)
from abi_coach.presentation import (
    BANNER,
    main,
    run_interactive_loop,
    should_inspect_screen,
)

# Orchestration & Legacy Slices (100% Backward Compatibility)
from abi_coach.core.audio import AudioListener, Speaker
from abi_coach.core.llm import LLMProvider, create_llm_provider
from abi_coach.core.vision import capture_screen
from abi_coach.orchestration import Brain, CoachResponse, Turn, load_preset
from abi_coach.slices.archetypes import ArchetypeManager, ArchetypeScaffolder, DynamicEntity, TopicContext
from abi_coach.slices.companion_memory import CompanionMemory, MemoryItem
from abi_coach.slices.metatuning import MetaTuningEngine, MetaTuningResult
from abi_coach.slices.reporting import create_html_report, create_tactical_dashboard
from abi_coach.slices.tactical_rag import KnowledgeItem, KnowledgeRAG, KnowledgeReconciler, ReconciliationDiff

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Domain
    "Result",
    "Success",
    "Failure",
    "ok",
    "fail",
    "DomainError",
    "EntityNotFoundError",
    "TopicKey",
    "ArmorTier",
    "ConfidenceScore",
    "TokenUsage",
    "GameContext",
    "PlayerMemory",
    "TacticalFact",
    "LLMProviderPort",
    "LLMResponseDTO",
    # Application
    "ExecutionPipeline",
    "ExceptionHandlingMiddleware",
    "LoggingMiddleware",
    "TacticalAdviceHandler",
    "AskTacticalAdviceCommand",
    "TacticalAdviceDTO",
    "ContextSwitchHandler",
    "CompanionMemoryHandler",
    "TacticalRagHandler",
    "MetaTuningHandler",
    # Infrastructure
    "AppConfig",
    "load_config",
    "create_llm_adapter",
    "GeminiAdapter",
    "NvidiaNimAdapter",
    "DatabaseManager",
    "MindCacheLRU",
    "SqliteKnowledgeRepository",
    "SqliteMemoryRepository",
    "FasterWhisperAudioInputAdapter",
    "EdgeTtsAudioOutputAdapter",
    "WindowsScreenCaptureAdapter",
    "BrowserDisplayAdapter",
    "TacticalReportBuilder",
    # Presentation
    "main",
    "run_interactive_loop",
    "should_inspect_screen",
    "BANNER",
    # Legacy & Shim Compatibility
    "AudioListener",
    "Speaker",
    "capture_screen",
    "LLMProvider",
    "create_llm_provider",
    "Brain",
    "CoachResponse",
    "Turn",
    "load_preset",
    "ArchetypeManager",
    "ArchetypeScaffolder",
    "DynamicEntity",
    "TopicContext",
    "KnowledgeItem",
    "KnowledgeRAG",
    "KnowledgeReconciler",
    "ReconciliationDiff",
    "CompanionMemory",
    "MemoryItem",
    "MetaTuningEngine",
    "MetaTuningResult",
    "create_html_report",
    "create_tactical_dashboard",
]
