"""LLM Adapter and Provider Factory (Infrastructure Layer)."""

import os
from abi_coach.domain.ports.llm_port import LLMProviderPort
from abi_coach.infrastructure.adapters.llm.base import LLMProvider
from abi_coach.infrastructure.adapters.llm.gemini import GeminiProvider
from abi_coach.infrastructure.adapters.llm.gemini_adapter import GeminiAdapter
from abi_coach.infrastructure.adapters.llm.nvidia import NvidiaNIMProvider
from abi_coach.infrastructure.adapters.llm.nvidia_adapter import NvidiaNimAdapter
from abi_coach.infrastructure.config.yaml_loader import AppConfig


from abi_coach.infrastructure.adapters.llm.moonshot_adapter import MoonshotAdapter
from abi_coach.infrastructure.adapters.llm.resilient_orchestrator import ResilientLLMOrchestrator
from abi_coach.infrastructure.config.settings import GeminiConfig


def _default_failover_handler(failed_name: str, reason: str, next_name: str) -> None:
    print(
        f"\n⚠️ [ROTACIÓN EN CALIENTE] Proveedor '{failed_name}' no disponible ({reason}).\n"
        f"   🔄 Conmutando instantáneamente a '{next_name}'...",
        flush=True,
    )


def create_llm_adapter(config: AppConfig) -> LLMProviderPort:
    """Factory instantiating LLM provider adapter according to configuration."""
    provider_type = (getattr(config.llm, "provider", "gemini") or "gemini").lower().strip()

    if provider_type == "nvidia":
        api_key = config.nvidia.api_key or os.getenv("NVIDIA_API_KEY", "")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY no encontrada. Configúrala en config.yaml o en .env")
        return NvidiaNimAdapter(config.nvidia, api_key=api_key)

    if provider_type == "moonshot":
        api_key = config.moonshot.api_key or os.getenv("MOONSHOT_API_KEY", "")
        if not api_key:
            raise ValueError("MOONSHOT_API_KEY no encontrada. Configúrala en config.yaml o en .env")
        return MoonshotAdapter(
            api_key=api_key,
            base_url=config.moonshot.base_url,
            model=config.moonshot.model,
            temperature=config.moonshot.temperature,
            max_tokens=config.moonshot.max_tokens,
            timeout_sec=config.moonshot.timeout_sec,
        )

    # Proveedor primario: Gemini
    gemini_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY no encontrada. Configúrala en config.yaml o en .env")

    primary_adapter = GeminiAdapter(config.gemini, api_key=gemini_key)
    primary_name = getattr(config.gemini, "model", "gemini-3.5-flash")

    # Si la orquestación resiliente no está habilitada, retornar adaptador directo
    resilience_cfg = getattr(config, "resilience", None)
    if not resilience_cfg or not getattr(resilience_cfg, "enabled", True):
        return primary_adapter

    # Construir cascada de proveedores de contingencia
    fallbacks: list = []
    cascade_names = getattr(resilience_cfg, "fallback_cascade", ["gemini-lite", "moonshot"])

    for item in cascade_names:
        item_lower = item.lower().strip()
        if item_lower in ("gemini-lite", "gemini_lite", "gemini-flash-lite"):
            lite_cfg = GeminiConfig(
                model="gemini-3.1-flash-lite-preview",
                media_resolution=config.gemini.media_resolution,
                temperature=config.gemini.temperature,
                api_key=gemini_key,
                game=config.gemini.game,
            )
            fallbacks.append(("gemini-3.1-flash-lite", GeminiAdapter(lite_cfg, api_key=gemini_key)))

        elif item_lower in ("moonshot", "kimi"):
            moonshot_key = config.moonshot.api_key or os.getenv("MOONSHOT_API_KEY", "")
            fallbacks.append(
                (
                    "kimi-moonshot",
                    MoonshotAdapter(
                        api_key=moonshot_key,
                        base_url=config.moonshot.base_url,
                        model=config.moonshot.model,
                        temperature=config.moonshot.temperature,
                        max_tokens=config.moonshot.max_tokens,
                        timeout_sec=config.moonshot.timeout_sec,
                    ),
                )
            )

        elif item_lower in ("nvidia", "nim"):
            nvd_key = config.nvidia.api_key or os.getenv("NVIDIA_API_KEY", "")
            fallbacks.append(("nvidia-nim", NvidiaNimAdapter(config.nvidia, api_key=nvd_key)))

    return ResilientLLMOrchestrator(
        primary=(primary_name, primary_adapter),
        fallbacks=fallbacks,
        failure_threshold=getattr(resilience_cfg, "failure_threshold", 2),
        recovery_timeout_sec=getattr(resilience_cfg, "recovery_timeout_sec", 30.0),
        on_failover=_default_failover_handler,
    )


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

