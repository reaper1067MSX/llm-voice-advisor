"""Backward compatibility shim for abi_coach.providers."""

from abi_coach.core.llm import (
    GeminiProvider,
    LLMProvider,
    NvidiaNIMProvider,
    ProviderResponse,
    create_llm_provider,
)

__all__ = [
    "GeminiProvider",
    "LLMProvider",
    "NvidiaNIMProvider",
    "ProviderResponse",
    "create_llm_provider",
]
