"""Base protocol and data contracts for LLM providers (Core LLM)."""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol


@dataclass
class ProviderResponse:
    spoken_text: str
    report_path: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: float = 0.0


class LLMProvider(Protocol):
    """Protocol for multimodal LLM backends (Gemini, NVIDIA NIM, local models)."""

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
        history_text: Optional[List[str]] = None,
        tool_callback: Optional[Callable[[str, str], str]] = None,
    ) -> ProviderResponse:
        """Execute multimodal generation using the underlying AI backend."""
        ...
