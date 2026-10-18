"""Clean Architecture Application Use Cases."""

from abi_coach.application.use_cases.context_switch import GameContextSwitchUseCase
from abi_coach.application.use_cases.context_switch_detector import ContextSwitchDetector
from abi_coach.domain.entities.interaction_records import CoachResponse, InteractionRequest, InteractionResult

__all__ = [
    "CoachResponse",
    "InteractionRequest",
    "InteractionResult",
    "GameContextSwitchUseCase",
    "ContextSwitchDetector",
]
