"""Application Vertical Slices package."""

from abi_coach.application.slices.companion_memory import (
    CompanionMemoryHandler,
    GetActiveProfileQuery,
    SaveMemoryCommand,
)
from abi_coach.application.slices.context_switching import (
    ContextSwitchHandler,
    SwitchContextCommand,
)
from abi_coach.application.slices.metatuning import (
    MetaTuningHandler,
    ProcessMetaTuningCommand,
)
from abi_coach.application.slices.tactical_advice import (
    AskTacticalAdviceCommand,
    TacticalAdviceDTO,
    TacticalAdviceHandler,
)
from abi_coach.application.slices.tactical_rag import (
    ReconcileFactCommand,
    SearchKnowledgeQuery,
    TacticalRagHandler,
)

__all__ = [
    # Tactical Advice
    "AskTacticalAdviceCommand",
    "TacticalAdviceDTO",
    "TacticalAdviceHandler",
    # Context Switching
    "SwitchContextCommand",
    "ContextSwitchHandler",
    # Companion Memory
    "SaveMemoryCommand",
    "GetActiveProfileQuery",
    "CompanionMemoryHandler",
    # Tactical RAG
    "SearchKnowledgeQuery",
    "ReconcileFactCommand",
    "TacticalRagHandler",
    # Meta Tuning
    "ProcessMetaTuningCommand",
    "MetaTuningHandler",
]
