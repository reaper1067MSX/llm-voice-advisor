"""NVIDIA NIM LLM Hexagonal Adapter implementing LLMProviderPort."""

import base64
import time
from typing import Any, Callable, Dict, List, Optional

from abi_coach.domain.common.errors import ProviderError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.common.value_objects import TokenUsage
from abi_coach.domain.ports.llm_port import LLMProviderPort, LLMResponseDTO
from abi_coach.infrastructure.config.yaml_loader import NvidiaConfig


class NvidiaNimAdapter(LLMProviderPort):
    """Hexagonal Adapter for NVIDIA NIM (OpenAI-compatible inference)."""

    def __init__(self, config: NvidiaConfig, api_key: str):
        self.config = config
        self.api_key = api_key
        try:
            from openai import OpenAI
            self.client = OpenAI(base_url=config.base_url, api_key=api_key)
        except ImportError:
            self.client = None

    def generate(
        self,
        prompt: str,
        system_instruction: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
        history_text: Optional[List[str]] = None,
        tool_callback: Optional[Callable[[str, str], str]] = None,
    ) -> Result[LLMResponseDTO, ProviderError]:
        if self.client is None:
            return fail(
                ProviderError(
                    code="OPENAI_PACKAGE_MISSING",
                    message="El paquete 'openai' no está instalado. Ejecuta: uv add openai",
                    provider_name="nvidia",
                    spoken_fallback="El proveedor NVIDIA requiere la librería cliente. Revisa la terminal.",
                )
            )

        start_time = time.perf_counter()
        try:
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": system_instruction}
            ]

            if history_text:
                hist_str = "\n".join(history_text)
                messages.append(
                    {"role": "user", "content": f"HISTORIAL PREVIO:\n{hist_str}"}
                )

            user_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]

            if image_bytes:
                b64_img = base64.b64encode(image_bytes).decode("utf-8")
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                    }
                )

            if crop_bytes:
                for region_name, c_bytes in crop_bytes.items():
                    b64_crop = base64.b64encode(c_bytes).decode("utf-8")
                    user_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_crop}"},
                        }
                    )

            messages.append({"role": "user", "content": user_content})

            max_tok = getattr(
                self.config, "max_tokens", getattr(self.config, "max_output_tokens", 500)
            )
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=max_tok,
            )

            latency = (time.perf_counter() - start_time) * 1000
            spoken_text = ""
            if getattr(response, "choices", None) and response.choices[0].message.content:
                spoken_text = response.choices[0].message.content.strip()
            usage = getattr(response, "usage", None)
            in_tok = getattr(usage, "prompt_tokens", 0) or 0
            out_tok = getattr(usage, "completion_tokens", 0) or 0

            return ok(
                LLMResponseDTO(
                    spoken_text=spoken_text,
                    tokens=TokenUsage(input_tokens=in_tok, output_tokens=out_tok),
                    latency_ms=latency,
                )
            )

        except Exception as e:
            return fail(
                ProviderError(
                    code="NVIDIA_INFERENCE_ERROR",
                    message=f"Error en inferencia de NVIDIA NIM: {e}",
                    provider_name="nvidia",
                    spoken_fallback="Error al comunicar con NVIDIA NIM. Verifica tu conexión y API key.",
                )
            )
