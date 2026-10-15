"""Google Gemini multimodal provider implementation."""

import time
from typing import Any, Callable, Dict, List, Optional
from google import genai
from google.genai import types

from abi_coach.config import GeminiConfig
from abi_coach.providers.base import ProviderResponse


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

        if history_text:
            contents.extend(history_text)

        if image_bytes:
            contents.append(
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type="image/jpeg",
                    media_resolution=media_res,
                )
            )

        if crop_bytes:
            for region_name, crop_data in crop_bytes.items():
                contents.append(f"[Recorte detallado nativo de región: {region_name}]")
                contents.append(
                    types.Part.from_bytes(
                        data=crop_data,
                        mime_type="image/jpeg",
                        media_resolution=media_res,
                    )
                )

        contents.append(f"JUGADOR: {prompt}")

        tools = [tool_callback] if tool_callback else None

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.config.temperature,
            media_resolution=media_res,
            tools=tools,
        )

        chat = self.client.chats.create(
            model=self.config.model,
            config=gen_config,
        )

        response = chat.send_message(contents)
        spoken_text = response.text or ""

        input_tokens = None
        output_tokens = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", None)

        duration_ms = (time.perf_counter() - start_time) * 1000

        return ProviderResponse(
            spoken_text=spoken_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=duration_ms,
        )
