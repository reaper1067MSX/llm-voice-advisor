"""Clean Architecture Application Use Cases."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CoachResponse:
    """Tactical coach response DTO containing spoken output, report path, and token metrics."""

    spoken_text: str
    report_path: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: float = 0.0
    provider_name: str = "gemini"


from abi_coach.application.use_cases.context_switch import GameContextSwitchUseCase
from abi_coach.application.use_cases.fast_path_query import FastPathQueryUseCase
from abi_coach.application.use_cases.tactical_advice import TacticalAdviceUseCase

__all__ = [
    "CoachResponse",
    "FastPathQueryUseCase",
    "GameContextSwitchUseCase",
    "TacticalAdviceUseCase",
]
