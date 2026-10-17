"""Google Gemini LLM Hexagonal Adapter implementing LLMProviderPort."""

import time
from typing import Any, Callable, Dict, List, Optional
from google import genai
from google.genai import types

from abi_coach.domain.common.errors import ProviderError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.common.value_objects import TokenUsage
from abi_coach.domain.ports.llm_port import LLMProviderPort, LLMResponseDTO
from abi_coach.infrastructure.config.yaml_loader import GeminiConfig


class GeminiAdapter(LLMProviderPort):
    """Hexagonal Adapter for Google GenAI SDK (Gemini Flash Multimodal)."""

    def __init__(self, config: GeminiConfig, api_key: str):
        self.config = config
        self.client = genai.Client(api_key=api_key)

    def _get_media_resolution(self) -> types.MediaResolution:
        res = (self.config.media_resolution or "high").lower()
        if res == "high":
            return types.MediaResolution.MEDIA_RESOLUTION_HIGH
        if res == "medium":
            return types.MediaResolution.MEDIA_RESOLUTION_MEDIUM
        if res == "low":
            return types.MediaResolution.MEDIA_RESOLUTION_LOW
        return types.MediaResolution.MEDIA_RESOLUTION_HIGH

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
        try:
            contents: List[Any] = []
            if image_bytes:
                contents.append(
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                )

            if crop_bytes:
                for region_name, c_bytes in crop_bytes.items():
                    contents.append(f"[Recorte de alta resolución de '{region_name}']")
                    contents.append(
                        types.Part.from_bytes(data=c_bytes, mime_type="image/jpeg")
                    )

            if history_text:
                contents.append("HISTORIAL RECIENTE DE LA CONVERSACIÓN:")
                contents.extend(history_text)

            contents.append(f"PREGUNTA DEL JUGADOR: {prompt}")

            tools_list: List[Any] = []
            if tool_callback:
                tools_list.append(tool_callback)

            max_out_tokens = getattr(
                self.config, "max_output_tokens", getattr(self.config, "max_tokens", 800)
            )
            afc_config = (
                types.AutomaticFunctionCallingConfig(disable=True)
                if hasattr(types, "AutomaticFunctionCallingConfig")
                else None
            )
            gen_config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=self.config.temperature,
                max_output_tokens=max_out_tokens,
                media_resolution=self._get_media_resolution(),
                tools=tools_list if tools_list else None,
                automatic_function_calling=afc_config,
            )

            response = self.client.models.generate_content(
                model=self.config.model,
                contents=contents,
                config=gen_config,
            )

            latency = (time.perf_counter() - start_time) * 1000
            report_title = None
            report_html = None
            if getattr(response, "function_calls", None):
                for fc in response.function_calls:
                    func_name = (getattr(fc, "name", "") or "").lower()
                    fc_args = getattr(fc, "args", {}) or {}
                    if any(
                        alias in func_name
                        for alias in ("create_report", "report_tool", "create_html_report", "report")
                    ):
                        report_title = fc_args.get("title", report_title)
                        report_html = fc_args.get("html_body", report_html)
                        if tool_callback:
                            try:
                                tool_callback(**fc_args)
                            except Exception:
                                pass

            spoken_text = (getattr(response, "text", None) or "").strip()
            usage = getattr(response, "usage_metadata", None)
            in_tok = getattr(usage, "prompt_token_count", 0) or 0
            out_tok = getattr(usage, "candidates_token_count", 0) or 0

            return ok(
                LLMResponseDTO(
                    spoken_text=spoken_text,
                    report_title=report_title,
                    report_html=report_html,
                    tokens=TokenUsage(input_tokens=in_tok, output_tokens=out_tok),
                    latency_ms=latency,
                )
            )

        except Exception as e:
            return fail(
                ProviderError(
                    code="GEMINI_INFERENCE_ERROR",
                    message=f"Error en inferencia de Gemini: {e}",
                    provider_name="gemini",
                    spoken_fallback="Disculpa, tuve un retraso al consultar mi modelo visual en la nube. Prueba a preguntarme de nuevo.",
                )
            )
