"""Orchestration package: central brain facade and multimodal inference pipeline."""

from abi_coach.orchestration.brain import (
    ABI_SYSTEM_INSTRUCTION,
    COACH_SYSTEM_INSTRUCTION,
    GENERIC_SYSTEM_INSTRUCTION,
    Brain,
    CoachResponse,
    Turn,
    load_preset,
)

__all__ = [
    "Brain",
    "CoachResponse",
    "Turn",
    "load_preset",
    "COACH_SYSTEM_INSTRUCTION",
    "ABI_SYSTEM_INSTRUCTION",
    "GENERIC_SYSTEM_INSTRUCTION",
]
