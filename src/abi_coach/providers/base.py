"""Backward compatibility shim for abi_coach.providers.base."""

from abi_coach.core.llm.base import LLMProvider, ProviderResponse

__all__ = ["LLMProvider", "ProviderResponse"]
