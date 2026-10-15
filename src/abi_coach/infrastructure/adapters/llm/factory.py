"""LLM Adapter Factory (Infrastructure Layer)."""

import os
from abi_coach.domain.ports.llm_port import LLMProviderPort
from abi_coach.infrastructure.adapters.llm.gemini_adapter import GeminiAdapter
from abi_coach.infrastructure.adapters.llm.nvidia_adapter import NvidiaNimAdapter
from abi_coach.infrastructure.config.yaml_loader import AppConfig


def create_llm_adapter(config: AppConfig) -> LLMProviderPort:
    """Factory instantiating LLM provider adapter according to configuration."""
    provider_type = (getattr(config.llm, "provider", "gemini") or "gemini").lower()

    if provider_type == "nvidia":
        api_key = config.nvidia.api_key or os.getenv("NVIDIA_API_KEY", "")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY no encontrada. Configúrala en config.yaml o en .env")
        return NvidiaNimAdapter(config.nvidia, api_key=api_key)

    api_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY no encontrada. Configúrala en config.yaml o en .env")
    return GeminiAdapter(config.gemini, api_key=api_key)
