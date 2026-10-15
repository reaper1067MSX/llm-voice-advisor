"""Tactical Advice Vertical Slice (Application Layer).

Coordinates multimodal question answering, visual analysis, fast-path factual retrieval,
and rich report generation.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result, ok
from abi_coach.domain.common.value_objects import TokenUsage


@dataclass(frozen=True)
class AskTacticalAdviceCommand:
    """Command requesting tactical advice during live gameplay."""

    prompt: str
    image_bytes: Optional[bytes] = None
    crop_bytes: Optional[Dict[str, bytes]] = None
    game_context: str = "generic"


@dataclass(frozen=True)
class TacticalAdviceDTO:
    """Result payload of a tactical advice operation."""

    spoken_advice: str
    report_path: Optional[str] = None
    tokens: TokenUsage = TokenUsage()
    latency_ms: float = 0.0
    is_fast_path: bool = False
