"""Domain Layer: pure enterprise business rules, DDD entities, value objects, and ports."""

from abi_coach.domain.common import (
    AmbiguousInstructionError,
    ArmorTier,
    ConfidenceScore,
    DomainError,
    EntityNotFoundError,
    Failure,
    ProviderError,
    Result,
    StorageError,
    Success,
    SystemUnexpectedError,
    TokenUsage,
    TopicKey,
    ValidationError,
    fail,
    ok,
)
from abi_coach.domain.entities import (
    GameContext,
    MetaTuningDirective,
    PlayerMemory,
    TacticalDiff,
    TacticalFact,
    TuningRule,
)
from abi_coach.domain.ports import (
    AudioInputPort,
    AudioOutputPort,
    KnowledgeRepositoryPort,
    LLMProviderPort,
    LLMResponseDTO,
    MemoryRepositoryPort,
    ReportDisplayPort,
    ScreenCapturePort,
    ScreenCaptureResultDTO,
)

__all__ = [
    # Result & Errors
    "Result",
    "Success",
    "Failure",
    "ok",
    "fail",
    "DomainError",
    "EntityNotFoundError",
    "ValidationError",
    "AmbiguousInstructionError",
    "ProviderError",
    "StorageError",
    "SystemUnexpectedError",
    # Value Objects
    "TopicKey",
    "ArmorTier",
    "ConfidenceScore",
    "TokenUsage",
    # Entities
    "GameContext",
    "PlayerMemory",
    "TacticalFact",
    "TacticalDiff",
    "TuningRule",
    "MetaTuningDirective",
    # Ports
    "LLMProviderPort",
    "LLMResponseDTO",
    "KnowledgeRepositoryPort",
    "MemoryRepositoryPort",
    "AudioInputPort",
    "AudioOutputPort",
    "ScreenCapturePort",
    "ScreenCaptureResultDTO",
    "ReportDisplayPort",
]
