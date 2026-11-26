"""Resilient LLM Orchestrator implementing Circuit Breaker and Fallback Cascade."""

import logging
from typing import Callable, Dict, List, Optional, Tuple

from abi_coach.domain.common.errors import ProviderError
from abi_coach.domain.common.result import Result, fail
from abi_coach.domain.ports.llm_port import LLMProviderPort, LLMResponseDTO
from abi_coach.infrastructure.adapters.llm.circuit_breaker import CircuitBreaker, CircuitState

logger = logging.getLogger("abi_coach.orchestrator")


class ResilientLLMOrchestrator(LLMProviderPort):
    """Orchestrates primary and fallback LLM providers with Circuit Breakers."""

    def __init__(
        self,
        primary: Tuple[str, LLMProviderPort],
        fallbacks: Optional[List[Tuple[str, LLMProviderPort]]] = None,
        failure_threshold: int = 2,
        recovery_timeout_sec: float = 30.0,
        on_failover: Optional[Callable[[str, str, str], None]] = None,
    ):
        self.primary_name, self.primary_provider = primary
        self.fallbacks = fallbacks or []
        self.on_failover = on_failover

        # Configuración de Circuit Breakers independientes por cada proveedor
        self.breakers: Dict[str, CircuitBreaker] = {}
        all_providers = [primary] + self.fallbacks
        for name, _ in all_providers:
            self.breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout_sec=recovery_timeout_sec,
            )

    def get_circuit_status(self) -> Dict[str, CircuitState]:
        """Return the current circuit states for all monitored providers."""
        return {name: breaker.get_state() for name, breaker in self.breakers.items()}

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
        history_text: Optional[List[str]] = None,
        tool_callback: Optional[Callable[[str, str], str]] = None,
    ) -> Result[LLMResponseDTO, ProviderError]:
        providers = [ (self.primary_name, self.primary_provider) ] + self.fallbacks
        last_error: Optional[ProviderError] = None

        for idx, (name, provider) in enumerate(providers):
            breaker = self.breakers[name]

            if not breaker.can_execute():
                logger.warning(
                    f"Circuit Breaker para '{name}' está ABIERTO (OPEN). "
                    "Saltando proveedor en caliente."
                )
                if idx + 1 < len(providers) and self.on_failover:
                    next_name = providers[idx + 1][0]
                    self.on_failover(name, "Circuito abierto por fallas previas", next_name)
                continue

            # Intentar generar con el proveedor activo
            try:
                res = provider.generate(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    image_bytes=image_bytes,
                    crop_bytes=crop_bytes,
                    history_text=history_text,
                    tool_callback=tool_callback,
                )
            except Exception as exc:  # noqa: BLE001
                err = ProviderError(
                    code=f"{name.upper()}_UNEXPECTED_ERROR",
                    message=f"Excepción inesperada en proveedor '{name}': {exc}",
                    provider_name=name,
                    is_transient=True,
                    retryable=False,
                )
                last_error = err
                breaker.record_failure(exc)
                logger.warning(f"Excepción no controlada en proveedor '{name}': {exc}")
                if idx + 1 < len(providers) and self.on_failover:
                    next_name = providers[idx + 1][0]
                    self.on_failover(name, f"Excepción inesperada: {exc}", next_name)
                continue

            if res.is_ok():
                breaker.record_success()
                return res

            # Si falla, registrar error en su Circuit Breaker
            err = res.error
            last_error = err
            breaker.record_failure(Exception(err.message))
            logger.warning(f"Falla en proveedor '{name}': {err.message}")

            # Si existe un siguiente proveedor en la cascada, notificar rotación
            if idx + 1 < len(providers):
                next_name = providers[idx + 1][0]
                if self.on_failover:
                    self.on_failover(name, err.message, next_name)

        # Si todos los proveedores fueron agotados o tienen el circuito abierto
        return fail(
            last_error
            or ProviderError(
                code="ALL_PROVIDERS_UNAVAILABLE",
                message=(
                    "Todos los proveedores de IA configurados están fuera de servicio o saturados."
                ),
                provider_name="resilient_orchestrator",
                spoken_fallback=(
                    "Disculpa, todos mis modelos en la nube están saturados en este momento. "
                    "Intenta de nuevo en unos segundos."
                ),
            )
        )
