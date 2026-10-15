"""NVIDIA NIM / OpenAI-compatible multimodal provider implementation."""

import base64
import time
from typing import Any, Callable, Dict, List, Optional

from abi_coach.config import NvidiaConfig
from abi_coach.providers.base import ProviderResponse


class NvidiaNIMProvider:
    """Multimodal provider for NVIDIA NIM (build.nvidia.com) via OpenAI-compatible endpoint."""

    def __init__(self, config: NvidiaConfig, api_key: str):
        self.config = config
        self.api_key = api_key
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "La biblioteca 'openai' es requerida para usar el proveedor NVIDIA NIM.\n"
                "Instálala ejecutando: uv add openai"
            )
        self.client = OpenAI(
            base_url=self.config.base_url,
            api_key=self.api_key,
        )

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
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_instruction}
        ]

        if history_text:
            for item in history_text:
                if ":" in item:
                    role_str, text_val = item.split(":", 1)
                    r = "assistant" if role_str.strip().lower() in ("coach", "assistant") else "user"
                    messages.append({"role": r, "content": text_val.strip()})
                else:
                    messages.append({"role": "user", "content": item})

        user_content: List[Dict[str, Any]] = []

        if image_bytes:
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_data}"},
            })

        if crop_bytes:
            for region_name, c_data in crop_bytes.items():
                b64_crop = base64.b64encode(c_data).decode("utf-8")
                user_content.append({"type": "text", "text": f"[Región: {region_name}]"})
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_crop}"},
                })

        user_content.append({"type": "text", "text": f"JUGADOR: {prompt}"})
        messages.append({"role": "user", "content": user_content})

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        spoken_text = response.choices[0].message.content or ""
        input_tokens = None
        output_tokens = None
        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "prompt_tokens", None)
            output_tokens = getattr(response.usage, "completion_tokens", None)

        duration_ms = (time.perf_counter() - start_time) * 1000

        return ProviderResponse(
            spoken_text=spoken_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=duration_ms,
        )
