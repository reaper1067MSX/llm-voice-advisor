"""Application Vertical Slices package."""

from abi_coach.application.slices.archetypes import (
    ArchetypeDefinition,
    ArchetypeManager,
    ArchetypeScaffolder,
    DynamicEntity,
    EngramObservation,
    TopicContext,
)
from abi_coach.application.slices.companion_memory import (
    CompanionMemory,
    CompanionMemoryHandler,
    GetActiveProfileQuery,
    MemoryItem,
    SaveMemoryCommand,
)
from abi_coach.application.slices.context_switching import (
    ContextSwitchHandler,
    SwitchContextCommand,
)
from abi_coach.application.slices.metatuning import (
    ClarificationState,
    MetaTuningEngine,
    MetaTuningHandler,
    MetaTuningResult,
    ProcessMetaTuningCommand,
)
from abi_coach.application.slices.reporting import (
    TacticalReportBuilder,
    create_html_report,
    create_tactical_dashboard,
    open_and_maximize_in_browser,
)
from abi_coach.application.slices.tactical_advice import (
    AskTacticalAdviceCommand,
    TacticalAdviceDTO,
    TacticalAdviceHandler,
)
from abi_coach.application.slices.tactical_rag import (
    KnowledgeItem,
    KnowledgeRAG,
    KnowledgeReconciler,
    ReconcileFactCommand,
    ReconciliationDiff,
    SearchKnowledgeQuery,
    TacticalRagHandler,
)

__all__ = [
    # Archetypes
    "ArchetypeDefinition",
    "ArchetypeManager",
    "ArchetypeScaffolder",
    "DynamicEntity",
    "EngramObservation",
    "TopicContext",
    # Tactical Advice
    "AskTacticalAdviceCommand",
    "TacticalAdviceDTO",
    "TacticalAdviceHandler",
    # Context Switching
    "SwitchContextCommand",
    "ContextSwitchHandler",
    # Companion Memory
    "CompanionMemory",
    "MemoryItem",
    "SaveMemoryCommand",
    "GetActiveProfileQuery",
    "CompanionMemoryHandler",
    # Tactical RAG
    "KnowledgeItem",
    "KnowledgeRAG",
    "KnowledgeReconciler",
    "ReconciliationDiff",
    "SearchKnowledgeQuery",
    "ReconcileFactCommand",
    "TacticalRagHandler",
    # Meta Tuning
    "ClarificationState",
    "MetaTuningEngine",
    "MetaTuningResult",
    "ProcessMetaTuningCommand",
    "MetaTuningHandler",
    # Reporting
    "TacticalReportBuilder",
    "create_html_report",
    "create_tactical_dashboard",
    "open_and_maximize_in_browser",
]

