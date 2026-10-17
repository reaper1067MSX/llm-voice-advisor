"""Backward-compatibility module aliasing AdvisorOrchestrator."""

from abi_coach.application.orchestration.advisor_orchestrator import AdvisorOrchestrator
from abi_coach.application.services.history_manager import Turn
from abi_coach.application.services.prompt_registry import (
    ABI_SYSTEM_INSTRUCTION,
    COACH_SYSTEM_INSTRUCTION,
    GENERIC_SYSTEM_INSTRUCTION,
    ONCE_HUMAN_SYSTEM_INSTRUCTION,
    load_preset,
)
from abi_coach.domain.entities.interaction_records import CoachResponse

Brain = AdvisorOrchestrator

__all__ = [
    "Brain",
    "AdvisorOrchestrator",
    "CoachResponse",
    "Turn",
    "load_preset",
    "ABI_SYSTEM_INSTRUCTION",
    "COACH_SYSTEM_INSTRUCTION",
    "GENERIC_SYSTEM_INSTRUCTION",
    "ONCE_HUMAN_SYSTEM_INSTRUCTION",
]
