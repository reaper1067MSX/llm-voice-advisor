"""Application Layer: Use cases, Vertical Slices, and Execution Pipeline."""

from abi_coach.application.pipeline import (
    ExceptionHandlingMiddleware,
    ExecutionPipeline,
    LoggingMiddleware,
    Middleware,
)
from abi_coach.application.slices import (
    AskTacticalAdviceCommand,
    CompanionMemoryHandler,
    ContextSwitchHandler,
    GetActiveProfileQuery,
    MetaTuningHandler,
    ProcessMetaTuningCommand,
    ReconcileFactCommand,
    SaveMemoryCommand,
    SearchKnowledgeQuery,
    SwitchContextCommand,
    TacticalAdviceDTO,
    TacticalAdviceHandler,
    TacticalRagHandler,
)

__all__ = [
    # Pipeline
    "Middleware",
    "ExceptionHandlingMiddleware",
    "LoggingMiddleware",
    "ExecutionPipeline",
    # Slices
    "AskTacticalAdviceCommand",
    "TacticalAdviceDTO",
    "TacticalAdviceHandler",
    "SwitchContextCommand",
    "ContextSwitchHandler",
    "SaveMemoryCommand",
    "GetActiveProfileQuery",
    "CompanionMemoryHandler",
    "SearchKnowledgeQuery",
    "ReconcileFactCommand",
    "TacticalRagHandler",
    "ProcessMetaTuningCommand",
    "MetaTuningHandler",
]
