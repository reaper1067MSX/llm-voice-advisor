"""Factory for instantiating the configured LLM provider."""

import os
from abi_coach.config import AppConfig
from abi_coach.providers.base import LLMProvider
from abi_coach.providers.gemini import GeminiProvider
from abi_coach.providers.nvidia import NvidiaNIMProvider


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

    # Default to Gemini
    api_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró GEMINI_API_KEY. Configúrala en el archivo .env o en config.yaml"
        )
    return GeminiProvider(config=config.gemini, api_key=api_key)
