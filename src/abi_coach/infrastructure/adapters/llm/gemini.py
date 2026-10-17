"""Google Gemini multimodal provider implementation (Core LLM)."""

import time
from typing import Any, Callable, Dict, List, Optional
from google import genai
from google.genai import types

from abi_coach.infrastructure.adapters.llm.base import ProviderResponse
from abi_coach.infrastructure.config.settings import GeminiConfig


class GeminiProvider:
    """Multimodal provider backed by Google GenAI SDK (Gemini Flash)."""

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
    ) -> ProviderResponse:
        start_time = time.perf_counter()
        media_res = self._get_media_resolution()
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

        afc_config = (
            types.AutomaticFunctionCallingConfig(disable=True)
            if hasattr(types, "AutomaticFunctionCallingConfig")
            else None
        )

        cfg = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.config.temperature,
            media_resolution=media_res,
            tools=tools_list if tools_list else None,
            automatic_function_calling=afc_config,
        )

        response = self.client.models.generate_content(
            model=self.config.model,
            contents=contents,
            config=cfg,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        report_path = None
        spoken_text = ""
        if getattr(response, "function_calls", None):
            for fc in response.function_calls:
                func_name = (getattr(fc, "name", "") or "").lower()
                fc_args = getattr(fc, "args", {}) or {}
                if tool_callback and any(
                    alias in func_name
                    for alias in ("create_report", "report_tool", "create_html_report", "report")
                ):
                    try:
                        report_path = tool_callback(**fc_args)
                    except Exception:
                        pass

        if getattr(response, "text", None):
            spoken_text = response.text.strip()

        input_tok = None
        output_tok = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tok = getattr(response.usage_metadata, "prompt_token_count", None)
            output_tok = getattr(response.usage_metadata, "candidates_token_count", None)

        return ProviderResponse(
            spoken_text=spoken_text,
            report_path=report_path,
            input_tokens=input_tok,
            output_tokens=output_tok,
            latency_ms=latency_ms,
        )
