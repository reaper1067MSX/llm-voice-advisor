"""LLM Adapter and Provider Factory (Infrastructure Layer)."""

import os
from abi_coach.domain.ports.llm_port import LLMProviderPort
from abi_coach.infrastructure.adapters.llm.base import LLMProvider
from abi_coach.infrastructure.adapters.llm.gemini import GeminiProvider
from abi_coach.infrastructure.adapters.llm.gemini_adapter import GeminiAdapter
from abi_coach.infrastructure.adapters.llm.nvidia import NvidiaNIMProvider
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


def create_llm_provider(config: AppConfig) -> LLMProvider:
    """Instantiate the appropriate LLM provider based on application configuration."""
    provider_name = (getattr(config.llm, "provider", "gemini") or "gemini").lower().strip()

    if provider_name in ("nvidia", "nim", "nvidia_nim"):
        api_key = config.nvidia.api_key or os.getenv(config.nvidia.api_key_env)
        if not api_key:
            raise ValueError(
                f"No se encontró clave para NVIDIA NIM ({config.nvidia.api_key_env}).\n"
                f"Configúrala en .env o como variable de entorno."
            )
        return NvidiaNIMProvider(config=config.nvidia, api_key=api_key)

    api_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró GEMINI_API_KEY. Configúrala en el archivo .env o en config.yaml"
        )
    return GeminiProvider(config=config.gemini, api_key=api_key)

