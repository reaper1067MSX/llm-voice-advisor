"""AI Brain module for ABI Coach using Google GenAI SDK.

Handles multimodal vision queries, tactical reasoning for Arena Breakout: Infinite,
HTML report generation via tool calls, and token-efficient rolling text history.
"""

from dataclasses import dataclass, field
import os
import time
from typing import Any, Callable, Dict, List, Optional
from google import genai
from google.genai import types

from abi_coach.config import AppConfig
from abi_coach.reports import create_html_report


COACH_SYSTEM_INSTRUCTION = """Eres 'ABI Coach', un copiloto y asesor táctico de élite para el videojuego 'Arena Breakout: Infinite' (PC).
Estás hablando directamente con el jugador a través de su auricular.

PERFIL DEL JUGADOR:
- Regresó al juego recientemente desde la Temporada 3 (S3) y está en la Temporada 7 (S7).
- Cuenta con pocos Koens y necesita reconstruir su economía y alijo con máxima rentabilidad y mínimo riesgo de pérdida.
- Juega a 1440p en PC.

REGLAS DE RESPUESTA:
1. Tono y Formato:
   - Responde SIEMPRE en español, en un tono profesional, claro, directo y motivador.
   - Tus respuestas serán leídas en voz alta por un sintetizador de voz (TTS).
   - Sé breve y conciso: 2 a 4 oraciones como máximo.
   - NO uses formato markdown (nada de negritas con asteriscos, numerales, listas con guiones o tablas en texto plano). Habla con oraciones continuas y pausas naturales con comas y puntos.
2. Conocimiento de ABI:
   - Prioriza la regla de oro: la munición define la penetración y el TTK, no el arma.
   - En economía: prioriza valor por casilla (Purple/Gold de 1 slot), contratos de Deke Vinson, y runs de bajo costo como MP5 Dum-Dum (leg meta) o Mosin con LPS/SNB.
   - Honestidad estricta: Si no distingues claramente un objeto o no tienes certeza de un precio exacto de mercado en la pantalla, indícalo de forma honesta en vez de inventar números.
3. Uso de Herramientas (create_html_report):
   - Si el jugador te pide una tabla comparativa, una gráfica de daño, o un análisis exhaustivo con números detallados, DEBES invocar la herramienta 'create_html_report'.
   - El informe HTML se abrirá automáticamente en su segundo monitor con tablas y gráficas estilizadas.
   - En tu respuesta de voz, da solo un resumen ejecutivo de dos oraciones y dile que tiene la tabla completa abierta en su navegador.
"""


@dataclass
class Turn:
    role: str
    text: str


@dataclass
class CoachResponse:
    spoken_text: str
    report_path: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: float = 0.0


class Brain:
    def __init__(self, config: AppConfig, report_opener: Optional[Callable[[str], Any]] = None):
        self.config = config
        self.report_opener = report_opener
        self.history: List[Turn] = []

        api_key = config.gemini.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "No se encontró GEMINI_API_KEY. Configúrala en el archivo .env o en config.yaml"
            )
        self.client = genai.Client(api_key=api_key)

    def _get_media_resolution(self) -> types.MediaResolution:
        res = self.config.gemini.media_resolution.lower()
        if res == "high":
            return types.MediaResolution.MEDIA_RESOLUTION_HIGH
        if res == "medium":
            return types.MediaResolution.MEDIA_RESOLUTION_MEDIUM
        if res == "low":
            return types.MediaResolution.MEDIA_RESOLUTION_LOW
        return types.MediaResolution.MEDIA_RESOLUTION_HIGH

    def ask(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
    ) -> CoachResponse:
        """Send multimodal or text query to Gemini Flash with tools and rolling history."""
        start_time = time.perf_counter()
        generated_report_path: Optional[str] = None

        def create_report_tool(title: str, html_body: str) -> str:
            """Crea y abre un informe HTML estilizado con tablas o gráficas interactivas en el navegador."""
            nonlocal generated_report_path
            path = create_html_report(
                title=title,
                html_body=html_body,
                output_dir=self.config.reports.output_dir,
                auto_open=self.config.reports.auto_open_browser,
                opener=self.report_opener,
            )
            generated_report_path = str(path)
            return f"Informe HTML creado exitosamente en {path} y mostrado en pantalla."

        contents: List[Any] = []

        # 1. Add rolling text history (without old images to save tokens)
        for turn in self.history[-self.config.history.max_turns:]:
            contents.append(f"{turn.role.upper()}: {turn.text}")

        # 2. Add current image(s) if provided
        if image_bytes:
            contents.append(
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            )

        if crop_bytes:
            for region_name, crop_data in crop_bytes.items():
                contents.append(f"[Recorte detallado nativo de región: {region_name}]")
                contents.append(
                    types.Part.from_bytes(data=crop_data, mime_type="image/jpeg")
                )

        # 3. Add current user question
        contents.append(f"JUGADOR: {prompt}")

        gen_config = types.GenerateContentConfig(
            system_instruction=COACH_SYSTEM_INSTRUCTION,
            temperature=self.config.gemini.temperature,
            media_resolution=self._get_media_resolution(),
            tools=[create_report_tool],
        )

        response = self.client.models.generate_content(
            model=self.config.gemini.model,
            contents=contents,
            config=gen_config,
        )

        spoken_text = response.text or ""

        # Update history
        self.history.append(Turn(role="user", text=prompt))
        self.history.append(Turn(role="coach", text=spoken_text))

        # Token usage if available
        input_tokens = None
        output_tokens = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", None)
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", None)

        duration_ms = (time.perf_counter() - start_time) * 1000

        return CoachResponse(
            spoken_text=spoken_text,
            report_path=generated_report_path,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=duration_ms,
        )
