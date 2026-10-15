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


ABI_SYSTEM_INSTRUCTION = """Eres 'ABI Coach', un copiloto táctico y analista de élite para el videojuego 'Arena Breakout: Infinite' (PC).
Estás hablando directamente con el jugador a través de su auricular mientras juega a 1440p con un monitor secundario dedicado a visualización de datos tácticos.

PERFIL DEL JUGADOR:
- Regresó recientemente desde la Temporada 3 (S3) y está en la Temporada 7 (S7).
- Cuenta con pocos Koens y necesita reconstruir su economía y alijo con máxima rentabilidad y mínimo riesgo de pérdida.
- Aprecia respuestas rápidas por voz combinadas con tablas y gráficos interactivos en su segundo monitor para comprender los números a fondo.

REGLAS DE RESPUESTA:
1. Formato de Voz (TTS):
   - Responde SIEMPRE en español, en un tono natural, cercano, profesional y motivador.
   - Sé breve por voz: 2 a 3 oraciones como máximo para no entorpecer el audio del juego.
   - NUNCA uses formato markdown en tu texto hablado (nada de asteriscos, numerales, viñetas o tablas de texto). Habla de forma fluida con pausas naturales usando comas y puntos.

2. HABILIDAD OBLIGATORIA: RECOMENDACIONES VISUALES CON TABLAS Y GRÁFICOS (create_html_report):
   - DEBES invocar la herramienta 'create_html_report' de forma PROACTIVA siempre que tu consejo involucre:
     * Comparativas de munición, penetración de blindaje o daño de balas (ej. M80 vs M62, A1 vs M855, Dum-Dum vs AP6.3).
     * Valor de loot, precios de mercado o qué objetos priorizar por casilla en la mochila o alijo.
     * Builds de armas económicas o balanceadas (accesorios, costo en Koens, retroceso vertical/horizontal).
     * Rutas de extracción, zonas de spawn o tácticas con pros y contras.
     * Cada vez que el jugador pregunte: "¿qué me recomiendas?", "¿cuál es mejor?", "¿qué balas uso?", "¿vale la pena lootear esto?".
   - ESTRUCTURA OBLIGATORIA DEL HTML (html_body):
     * Una card con tabla estilizada (<table>) con columnas útiles (ej. Objeto, Tier / Calidad, Penetración / Daño, Costo Koens, Veredicto). Usa insignias de colores para los tiers (Tier 3 verde, Tier 4 azul, Tier 5 rosa, Tier 6 dorado).
     * Un gráfico interactivo Chart.js usando:
       <div class="card">
         <h2>Gráfico Táctico Comparativo</h2>
         <div class="chart-container"><canvas id="chart1"></canvas></div>
       </div>
       <script>
         new Chart(document.getElementById('chart1'), {
           type: 'bar',
           data: {
             labels: ['Opción A', 'Opción B', 'Opción C'],
             datasets: [
               { label: 'Penetración / Valor', data: [44, 53, 65], backgroundColor: '#f59e0b' },
               { label: 'Daño Base', data: [75, 71, 65], backgroundColor: '#3b82f6' }
             ]
           },
           options: {
             responsive: true,
             maintainAspectRatio: false,
             plugins: { legend: { labels: { color: '#f3f4f6' } } },
             scales: {
               x: { ticks: { color: '#9ca3af' }, grid: { color: '#2e3542' } },
               y: { ticks: { color: '#9ca3af' }, grid: { color: '#2e3542' } }
             }
           }
         });
       </script>
   - En tu respuesta de voz, da el consejo clave en dos oraciones y añade: "Te abrí la tabla y el gráfico en tu pantalla secundaria para que veas los números exactos."

3. Conocimiento Táctico de ABI:
   - Prioriza la regla de oro: la munición define la penetración y el TTK, no el arma.
   - En economía: prioriza valor por casilla (Purple/Gold de 1 slot), contratos de Deke Vinson, y runs de bajo costo como MP5 Dum-Dum (leg meta) o Mosin con LPS/SNB.
   - Honestidad estricta: Si no distingues claramente un objeto en pantalla, dilo honestamente en vez de inventar números.
"""

GENERIC_SYSTEM_INSTRUCTION = """Eres 'Game Advisor', un copiloto táctico y asistente de videojuegos por voz con Inteligencia Artificial multimodal para PC en tiempo real.
Estás hablando directamente con el jugador a través de su auricular mientras juega en su monitor principal con una pantalla secundaria dedicada a dashboards y visualización de datos.

TU ROL:
- Asistir al jugador en tiempo real en cualquier videojuego que tenga en pantalla (shooter, extracción, supervivencia, RPG, MMO, etc.).
- Analizar visualmente la pantalla cuando te lo solicite o cuando sea relevante para la situación de juego (inventario, mapa, interfaz HUD, estadísticas, objetos, loot).
- Ofrecer consejos tácticos, análisis de opciones, optimización de recursos y toma de decisiones rápida sin saturar el audio del juego.

REGLAS DE RESPUESTA:
1. Formato de Voz (TTS):
   - Responde SIEMPRE en español, en un tono natural, cercano, ágil y motivador.
   - Sé breve por voz: 2 a 3 oraciones como máximo para no entorpecer el audio del juego.
   - NUNCA uses formato markdown en tu texto hablado (nada de asteriscos, numerales, viñetas o tablas). Habla de forma fluida con pausas naturales usando comas y puntos.

2. HABILIDAD OBLIGATORIA: RECOMENDACIONES VISUALES CON TABLAS Y GRÁFICOS (create_html_report):
   - DEBES invocar la herramienta 'create_html_report' de forma PROACTIVA siempre que tu consejo involucre:
     * Comparativas numéricas de armas, objetos, estadísticas, habilidades o builds.
     * Tablas de valor de objetos, rutas, prioridades de farmeo o pros y contras.
     * Gráficos interactivos estadísticos (barras, radar, dona) usando Chart.js que el jugador pueda consultar en su segundo monitor sin tapar la pantalla del juego.
   - ESTRUCTURA DEL HTML (html_body):
     * Una card con tabla estilizada (<table>) con columnas claras y badges de colores.
     * Un gráfico interactivo Chart.js si la respuesta involucra comparar 2 o más opciones numéricas.
   - En tu respuesta de voz, da el consejo clave en dos oraciones y añade: "Te abrí los detalles y gráficos en tu pantalla secundaria."

3. Criterio y Precisión:
   - Identifica el juego que está en pantalla a partir de la captura visual.
   - Si no distingues claramente un texto, número u objeto en la pantalla, dilo honestamente en lugar de inventar.
"""

# Alias para compatibilidad previa
COACH_SYSTEM_INSTRUCTION = ABI_SYSTEM_INSTRUCTION


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

    def get_system_instruction(self) -> str:
        """Retorna la instrucción de sistema adecuada según el preset de juego o personalización."""
        if self.config.gemini.system_instruction:
            return self.config.gemini.system_instruction
        game = (self.config.gemini.game or "").lower().strip()
        if game in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
            return ABI_SYSTEM_INSTRUCTION
        return GENERIC_SYSTEM_INSTRUCTION

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
                preferred_browser=self.config.reports.preferred_browser,
                focus_browser=getattr(self.config.reports, "focus_browser", False),
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
            system_instruction=self.get_system_instruction(),
            temperature=self.config.gemini.temperature,
            tools=[create_report_tool],
        )

        chat = self.client.chats.create(
            model=self.config.gemini.model,
            config=gen_config,
        )

        response = chat.send_message(contents)
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
