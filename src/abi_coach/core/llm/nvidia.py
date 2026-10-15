"""NVIDIA NIM / OpenAI-compatible multimodal provider implementation (Core LLM)."""

import base64
import time
from typing import Any, Callable, Dict, List, Optional

from abi_coach.core.config import NvidiaConfig
from abi_coach.core.llm.base import ProviderResponse


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
            hist_str = "\n".join(history_text)
            messages.append(
                {"role": "system", "content": f"HISTORIAL RECIENTE:\n{hist_str}"}
            )

        user_content: List[Dict[str, Any]] = [
            {"type": "text", "text": prompt}
        ]

        if image_bytes:
            b64_img = base64.b64encode(image_bytes).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}
            })

        if crop_bytes:
            for region_name, c_bytes in crop_bytes.items():
                b64_crop = base64.b64encode(c_bytes).decode("utf-8")
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_crop}"}
                })

        messages.append({"role": "user", "content": user_content})

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        spoken_text = ""
        if response.choices and response.choices[0].message.content:
            spoken_text = response.choices[0].message.content.strip()

        input_tok = None
        output_tok = None
        if hasattr(response, "usage") and response.usage:
            input_tok = getattr(response.usage, "prompt_tokens", None)
            output_tok = getattr(response.usage, "completion_tokens", None)

        return ProviderResponse(
            spoken_text=spoken_text,
            report_path=None,
            input_tokens=input_tok,
            output_tokens=output_tok,
            latency_ms=latency_ms,
        )
