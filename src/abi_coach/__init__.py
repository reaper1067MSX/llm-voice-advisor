"""LLM Voice Advisor & Tactical Copilot (ABI Coach).

A real-time voice gaming copilot with local GPU Whisper STT, Natural Edge-TTS,
multimodal LLM inference, Vertical Slice Architecture, and dynamic secondary-monitor dashboards.
"""

# Core
from abi_coach.core.audio import AudioListener, Speaker
from abi_coach.core.config import AppConfig, load_config
from abi_coach.core.llm import LLMProvider, create_llm_provider
from abi_coach.core.storage import DatabaseManager, MindCacheLRU
from abi_coach.core.vision import capture_screen

# Entrypoints
from abi_coach.entrypoints import main, run_interactive_loop

# Orchestration
from abi_coach.orchestration import Brain, CoachResponse, Turn, load_preset

# Slices
from abi_coach.slices.archetypes import ArchetypeManager, ArchetypeScaffolder, DynamicEntity, TopicContext
from abi_coach.slices.companion_memory import CompanionMemory, MemoryItem
from abi_coach.slices.metatuning import MetaTuningEngine, MetaTuningResult
from abi_coach.slices.reporting import TacticalReportBuilder, create_html_report, create_tactical_dashboard
from abi_coach.slices.tactical_rag import KnowledgeItem, KnowledgeRAG, KnowledgeReconciler, ReconciliationDiff

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # Core
    "AppConfig",
    "load_config",
    "DatabaseManager",
    "MindCacheLRU",
    "AudioListener",
    "Speaker",
    "capture_screen",
    "LLMProvider",
    "create_llm_provider",
    # Slices
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
    "TacticalReportBuilder",
    "create_html_report",
    "create_tactical_dashboard",
    # Orchestration
    "Brain",
    "CoachResponse",
    "Turn",
    "load_preset",
    # Entrypoints
    "main",
    "run_interactive_loop",
]
