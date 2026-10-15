"""Domain common primitives: Result, Value Objects, and Domain Errors."""

from abi_coach.domain.common.errors import (
    AmbiguousInstructionError,
    DomainError,
    EntityNotFoundError,
    ProviderError,
    StorageError,
    SystemUnexpectedError,
    ValidationError,
)
from abi_coach.domain.common.result import (
    Failure,
    Result,
    ResultHelper,
    Success,
    fail,
    ok,
)
from abi_coach.domain.common.value_objects import (
    ArmorTier,
    ConfidenceScore,
    TokenUsage,
    TopicKey,
)

__all__ = [
    # Result
    "Result",
    "Success",
    "Failure",
    "ok",
    "fail",
    "ResultHelper",
    # Errors
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
]
