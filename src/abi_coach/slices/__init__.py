"""Vertical Slices architecture: autonomous domain capabilities of ABI Voice Coach."""

from abi_coach.slices.archetypes import ArchetypeManager, ArchetypeScaffolder, DynamicEntity, EngramObservation, TopicContext
from abi_coach.slices.companion_memory import CompanionMemory, MemoryItem
from abi_coach.slices.metatuning import MetaTuningEngine, MetaTuningResult
from abi_coach.slices.reporting import TacticalReportBuilder, create_html_report, create_tactical_dashboard
from abi_coach.slices.tactical_rag import KnowledgeItem, KnowledgeRAG, KnowledgeReconciler, ReconciliationDiff

__all__ = [
    # Archetypes
    "ArchetypeManager",
    "ArchetypeScaffolder",
    "DynamicEntity",
    "EngramObservation",
    "TopicContext",
    # Tactical RAG
    "KnowledgeItem",
    "KnowledgeRAG",
    "KnowledgeReconciler",
    "ReconciliationDiff",
    # Companion Memory
    "CompanionMemory",
    "MemoryItem",
    # Meta-Tuning
    "MetaTuningEngine",
    "MetaTuningResult",
    # Reporting
    "TacticalReportBuilder",
    "create_html_report",
    "create_tactical_dashboard",
]
