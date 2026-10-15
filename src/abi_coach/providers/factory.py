"""Backward compatibility shim for abi_coach.providers.factory."""

from abi_coach.core.llm.factory import create_llm_provider

__all__ = ["create_llm_provider"]
