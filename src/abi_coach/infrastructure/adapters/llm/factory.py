"""LLM Adapter and Provider Factory (Infrastructure Layer)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from abi_coach.application.services.model_discovery import DiscoveredModelsReport

from abi_coach.domain.ports.llm_port import LLMProviderPort
from abi_coach.infrastructure.adapters.llm.base import LLMProvider
from abi_coach.infrastructure.adapters.llm.gemini import GeminiProvider
from abi_coach.infrastructure.adapters.llm.gemini_adapter import GeminiAdapter
from abi_coach.infrastructure.adapters.llm.moonshot_adapter import MoonshotAdapter
from abi_coach.infrastructure.adapters.llm.nvidia import NvidiaNIMProvider
from abi_coach.infrastructure.adapters.llm.nvidia_adapter import NvidiaNimAdapter
from abi_coach.infrastructure.adapters.llm.resilient_orchestrator import (
    ResilientLLMOrchestrator,
)
from abi_coach.infrastructure.config.settings import GeminiConfig
from abi_coach.infrastructure.config.yaml_loader import AppConfig


def _default_failover_handler(failed_name: str, reason: str, next_name: str) -> None:
    print(
        f"\n⚠️ [ROTACIÓN EN CALIENTE] Proveedor '{failed_name}' no disponible ({reason}).\n"
        f"   🔄 Conmutando instantáneamente a '{next_name}'...",
        flush=True,
    )


def create_llm_adapter(
    config: AppConfig,
    discovered_report: Optional[DiscoveredModelsReport] = None,
) -> LLMProviderPort:
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
        msh_url = (
            discovered_report.moonshot_base_url
            if discovered_report
            else config.moonshot.base_url
        )
        msh_model = (
            discovered_report.moonshot_model
            if discovered_report
            else config.moonshot.model
        )
        return MoonshotAdapter(
            api_key=api_key,
            base_url=msh_url,
            model=msh_model,
            temperature=config.moonshot.temperature,
            max_tokens=config.moonshot.max_tokens,
            timeout_sec=config.moonshot.timeout_sec,
        )

    # Proveedor primario: Gemini
    gemini_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY no encontrada. Configúrala en config.yaml o en .env")

    primary_name = getattr(config.gemini, "model", "gemini-3.5-flash")
    if discovered_report and discovered_report.gemini_models:
        if primary_name not in discovered_report.gemini_models:
            primary_name = discovered_report.best_gemini_model(fallback=primary_name)

    primary_cfg = GeminiConfig(
        model=primary_name,
        media_resolution=config.gemini.media_resolution,
        temperature=config.gemini.temperature,
        max_output_tokens=config.gemini.max_output_tokens,
        thinking_budget=config.gemini.thinking_budget,
        api_key=gemini_key,
        game=config.gemini.game,
        system_instruction=config.gemini.system_instruction,
    )
    primary_adapter = GeminiAdapter(primary_cfg, api_key=gemini_key)

    # Si la orquestación resiliente no está habilitada, retornar adaptador directo
    resilience_cfg = getattr(config, "resilience", None)
    if not resilience_cfg or not getattr(resilience_cfg, "enabled", True):
        return primary_adapter

    # Construir cascada de proveedores de contingencia
    fallbacks: list = []
    if discovered_report is not None:
        cascade_names: List[str] = discovered_report.build_fallback_cascade(include_nvidia=True)
    else:
        cascade_names = list(
            getattr(resilience_cfg, "fallback_cascade", ["gemini-lite", "moonshot"])
        )

    for item in cascade_names:
        item_lower = item.lower().strip()
        if item_lower in ("gemini-lite", "gemini_lite", "gemini-flash-lite"):
            lite_model = None
            if discovered_report and discovered_report.gemini_models:
                candidates = [
                    "gemini-3.1-flash-lite",
                    "gemini-3.1-flash-lite-preview",
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-preview",
                ]
                for cand in candidates:
                    if cand in discovered_report.gemini_models and cand != primary_name:
                        lite_model = cand
                        break
            elif not discovered_report:
                lite_model = "gemini-3.1-flash-lite-preview"

            if lite_model:
                lite_cfg = GeminiConfig(
                    model=lite_model,
                    media_resolution=config.gemini.media_resolution,
                    temperature=config.gemini.temperature,
                    api_key=gemini_key,
                    game=config.gemini.game,
                )
                fallbacks.append((lite_model, GeminiAdapter(lite_cfg, api_key=gemini_key)))

        elif item_lower in ("moonshot", "kimi"):
            moonshot_key = config.moonshot.api_key or os.getenv("MOONSHOT_API_KEY", "")
            msh_url = (
                discovered_report.moonshot_base_url
                if discovered_report
                else config.moonshot.base_url
            )
            msh_model = (
                discovered_report.moonshot_model
                if discovered_report
                else config.moonshot.model
            )
            fallbacks.append(
                (
                    "kimi-moonshot",
                    MoonshotAdapter(
                        api_key=moonshot_key,
                        base_url=msh_url,
                        model=msh_model,
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
