"""Domain records for tactical interactions and query results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class InteractionRequest:
    """Generic tactical interaction request agnostic to specific games or domains."""

    prompt: str
    image_bytes: Optional[bytes] = None
    crop_bytes: Optional[Dict[str, bytes]] = None
    context_id: Optional[str] = None


@dataclass(frozen=True)
class InteractionResult:
    """Tactical interaction result returned by the orchestrator."""

    spoken_text: str
    report_path: Optional[str] = None
    input_tokens: Optional[int] = 0
    output_tokens: Optional[int] = 0
    latency_ms: float = 0.0
    provider_name: Optional[str] = None


# Backward-compatible alias
CoachResponse = InteractionResult
