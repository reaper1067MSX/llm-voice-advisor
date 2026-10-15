"""Domain Errors Hierarchy for Business Rules and Failure Representation.

All expected failures subclass DomainError and provide spoken feedback
suitable for text-to-speech without disrupting gameplay.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DomainError:
    """Base domain error carrying a semantic error code and user-facing message."""

    code: str
    message: str
    spoken_fallback: Optional[str] = None

    def get_spoken_message(self) -> str:
        """Return spoken text suitable for TTS, falling back to message."""
        return self.spoken_fallback or self.message


@dataclass(frozen=True)
class EntityNotFoundError(DomainError):
    """Raised when a requested domain entity (game context, memory, fact) does not exist."""

    entity_id: str = ""

    def __post_init__(self):
        if not self.spoken_fallback:
            object.__setattr__(
                self,
                "spoken_fallback",
                f"No encontré información sobre {self.entity_id or 'el elemento solicitado'}.",
            )


@dataclass(frozen=True)
class ValidationError(DomainError):
    """Raised when an invariant or input validation rule is violated."""

    field_name: str = ""


@dataclass(frozen=True)
class AmbiguousInstructionError(DomainError):
    """Raised when an instruction lacks sufficient actionable detail (needs clarification)."""

    clarification_question: str = ""

    def get_spoken_message(self) -> str:
        return self.clarification_question or self.message


@dataclass(frozen=True)
class ProviderError(DomainError):
    """Raised when an external model provider (Gemini / NVIDIA) returns an expected operational error."""

    provider_name: str = "generic"
    is_transient: bool = False


@dataclass(frozen=True)
class StorageError(DomainError):
    """Raised when a repository operation encounters an expected domain constraint violation."""

    operation: str = "query"


@dataclass(frozen=True)
class SystemUnexpectedError(DomainError):
    """Constructed by ExceptionHandlingMiddleware when an unexpected exception is trapped."""

    technical_detail: str = ""

    def __post_init__(self):
        if not self.spoken_fallback:
            object.__setattr__(
                self,
                "spoken_fallback",
                "Se produjo un fallo temporal en el motor del sistema. La escucha sigue activa.",
            )
