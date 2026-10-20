"""Moonshot AI (Kimi) Hexagonal Adapter implementing LLMProviderPort."""

import time
from typing import Any, Callable, Dict, List, Optional

import httpx

from abi_coach.domain.common.errors import ProviderError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.common.value_objects import TokenUsage
from abi_coach.domain.ports.llm_port import LLMProviderPort, LLMResponseDTO


class MoonshotAdapter(LLMProviderPort):
    """Hexagonal Adapter for Moonshot AI (Kimi) using standard OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.moonshot.ai/v1",
        model: str = "kimi-k2.6",
        temperature: float = 0.3,
        max_tokens: int = 250,
        timeout_sec: float = 6.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_sec = timeout_sec
        self._client = httpx.Client(timeout=timeout_sec)

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
        history_text: Optional[List[str]] = None,
        tool_callback: Optional[Callable[[str, str], str]] = None,
    ) -> Result[LLMResponseDTO, ProviderError]:
        start_time = time.perf_counter()

        if not self.api_key:
            return fail(
                ProviderError(
                    code="MOONSHOT_AUTH_ERROR",
                    message="MOONSHOT_API_KEY no configurada.",
                    provider_name="moonshot",
                    spoken_fallback="La clave de Kimi no está configurada.",
                )
            )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_instruction}
        ]

        if history_text:
            hist_str = "\n".join(history_text)
            messages.append({"role": "system", "content": f"HISTORIAL RECIENTE:\n{hist_str}"})

        # Si se envió imagen pero el modelo es puramente de texto, se indica contextualmente
        user_prompt = prompt
        if image_bytes:
            user_prompt = f"[Captura de pantalla adjunta]\n{prompt}"

        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}/chat/completions"

        try:
            resp = self._client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                err_msg = resp.text
                err_type = ""
                try:
                    err_json = resp.json().get("error", {})
                    if isinstance(err_json, dict):
                        err_msg = err_json.get("message", resp.text)
                        err_type = str(err_json.get("type", ""))
                    elif isinstance(err_json, str):
                        err_msg = err_json
                except (ValueError, KeyError, AttributeError):
                    pass

                if resp.status_code == 429:
                    is_quota = (
                        "exceeded_current_quota_error" in err_type
                        or "insufficient_balance" in err_type
                        or "quota" in err_type.lower()
                        or "quota" in err_msg.lower()
                        or "insufficient" in err_msg.lower()
                        or "balance" in err_msg.lower()
                    )
                    if is_quota:
                        return fail(
                            ProviderError(
                                code="MOONSHOT_QUOTA_ERROR",
                                message=(
                                    f"Cuota agotada o saldo insuficiente en Moonshot: {err_msg}"
                                ),
                                provider_name="moonshot",
                                is_transient=True,
                                retryable=False,
                                spoken_fallback=(
                                    "La cuota de Kimi está agotada. "
                                    "Conmutando a proveedor de respaldo."
                                ),
                            )
                        )
                    return fail(
                        ProviderError(
                            code="MOONSHOT_RATE_LIMIT",
                            message=f"Límite de tasa excedido en Moonshot: {err_msg}",
                            provider_name="moonshot",
                            is_transient=True,
                            retryable=True,
                            spoken_fallback=(
                                "Kimi está recibiendo demasiadas peticiones. "
                                "Reintentando con respaldo."
                            ),
                        )
                    )

                return fail(
                    ProviderError(
                        code=f"MOONSHOT_HTTP_{resp.status_code}",
                        message=f"Error HTTP {resp.status_code} desde Moonshot: {err_msg}",
                        provider_name="moonshot",
                        is_transient=(resp.status_code >= 500),
                        retryable=False,
                        spoken_fallback="Disculpa, hubo un problema al comunicarme con Kimi.",
                    )
                )

            data = resp.json()
            latency = (time.perf_counter() - start_time) * 1000

            choices = data.get("choices", [])
            if not choices:
                return fail(
                    ProviderError(
                        code="MOONSHOT_EMPTY_RESPONSE",
                        message="Respuesta vacía desde Moonshot API",
                        provider_name="moonshot",
                        spoken_fallback="Kimi no devolvió contenido.",
                    )
                )

            spoken_text = choices[0].get("message", {}).get("content", "").strip()
            usage = data.get("usage", {})
            in_tok = usage.get("prompt_tokens", 0) or 0
            out_tok = usage.get("completion_tokens", 0) or 0

            return ok(
                LLMResponseDTO(
                    spoken_text=spoken_text,
                    report_title=None,
                    report_html=None,
                    tokens=TokenUsage(input_tokens=in_tok, output_tokens=out_tok),
                    latency_ms=latency,
                    provider_name="moonshot",
                )
            )

        except (httpx.HTTPError, OSError) as e:
            latency = (time.perf_counter() - start_time) * 1000
            return fail(
                ProviderError(
                    code="MOONSHOT_NETWORK_ERROR",
                    message=f"Error de conexión con Moonshot (Kimi): {e}",
                    provider_name="moonshot",
                    is_transient=True,
                    retryable=True,
                    spoken_fallback="Hubo un error de conexión con Kimi.",
                )
            )
