"""LLM Provider Outbound Port (Domain Layer)."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol
from abi_coach.domain.common.errors import ProviderError
from abi_coach.domain.common.result import Result
from abi_coach.domain.common.value_objects import TokenUsage


@dataclass(frozen=True)
class LLMResponseDTO:
    """Standardized response from an AI provider."""

    spoken_text: str
    report_title: Optional[str] = None
    report_html: Optional[str] = None
    tokens: TokenUsage = TokenUsage()
    latency_ms: float = 0.0


class LLMProviderPort(Protocol):
    """Port for multimodal and text AI generation (Gemini, NVIDIA NIM)."""

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
        history_text: Optional[List[str]] = None,
        tool_callback: Optional[Callable[[str, str], str]] = None,
    ) -> Result[LLMResponseDTO, ProviderError]:
        """Generate response given multimodal inputs, returning Result."""
        ...
