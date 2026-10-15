"""AI Brain facade module for ABI Voice Coach (Orchestration Layer).

Handles multimodal vision queries, tactical reasoning, HTML report generation via tool calls,
token-efficient rolling text history, and coordinating memory, RAG, archetypes, and meta-tuning.
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Dict, List, Optional
from google import genai
from google.genai import types

from abi_coach.core.config import AppConfig
from abi_coach.core.llm.base import LLMProvider
from abi_coach.core.llm.factory import create_llm_provider
from abi_coach.core.storage.db import DatabaseManager
from abi_coach.slices.archetypes.manager import ArchetypeManager, TopicContext
from abi_coach.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.slices.companion_memory.memory import CompanionMemory, MemoryItem
from abi_coach.slices.metatuning.engine import MetaTuningEngine, MetaTuningResult
from abi_coach.slices.reporting.reports import create_html_report
from abi_coach.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG
from abi_coach.slices.tactical_rag.reconciler import KnowledgeReconciler, ReconciliationDiff


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


_PRESET_CACHE: Dict[str, str] = {}


def load_preset(game_name: str) -> str:
    """Load game system instruction markdown from presets directory with in-memory cache."""
    clean_name = (game_name or "").lower().strip()
    canonical = (
        "abi"
        if clean_name in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout")
        else "generic"
    )
    if canonical in _PRESET_CACHE:
        return _PRESET_CACHE[canonical]

    import sys

    # Search for presets directory across base_dir, _MEIPASS, and parent directories
    preset_candidates = []
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        preset_candidates.append(base / "presets" / f"{canonical}.md")
        if hasattr(sys, "_MEIPASS"):
            preset_candidates.append(Path(sys._MEIPASS) / "presets" / f"{canonical}.md")

    cur_file = Path(__file__).resolve()
    for p in cur_file.parents:
        preset_candidates.append(p / "presets" / f"{canonical}.md")

    preset_path = None
    for cand in preset_candidates:
        if cand.is_file():
            preset_path = cand
            break

    if preset_path and preset_path.is_file():
        try:
            text = preset_path.read_text(encoding="utf-8").strip()
            _PRESET_CACHE[canonical] = text
            return text
        except Exception:
            pass

    fallback = ABI_SYSTEM_INSTRUCTION if canonical == "abi" else GENERIC_SYSTEM_INSTRUCTION
    _PRESET_CACHE[canonical] = fallback
    return fallback


class Brain:
    """Unifying Facade coordinating LLM inference, Archetypes, Memory, RAG, and Meta-Tuning."""

    def __init__(
        self,
        config: AppConfig,
        report_opener: Optional[Callable[[str], Any]] = None,
        provider: Optional[LLMProvider] = None,
        memory: Optional[CompanionMemory] = None,
        rag: Optional[KnowledgeRAG] = None,
        reconciler: Optional[KnowledgeReconciler] = None,
        db: Optional[DatabaseManager] = None,
    ):
        self.config = config
        self.report_opener = report_opener
        self.history: List[Turn] = []

        if provider is not None:
            self.provider = provider
        else:
            self.provider = create_llm_provider(config)

        if db is not None:
            self.db = db
        elif memory and hasattr(memory, "db"):
            self.db = memory.db
        elif rag and hasattr(rag, "db"):
            self.db = rag.db
        elif reconciler and hasattr(reconciler, "db"):
            self.db = reconciler.db
        else:
            self.db = DatabaseManager()

        self.archetype_mgr = ArchetypeManager(self.db)
        self.scaffolder = ArchetypeScaffolder(self.db, self.archetype_mgr)
        self.active_context_id = getattr(config.gemini, "game", "generic") or "generic"
        self._last_report_path: Optional[str] = None

        if memory is not None:
            self.memory = memory
        else:
            self.memory = CompanionMemory(
                self.db, default_game=self.active_context_id
            )

        if rag is not None:
            self.rag = rag
        else:
            self.rag = KnowledgeRAG(
                self.db, default_game=self.active_context_id
            )

        if reconciler is not None:
            self.reconciler = reconciler
        else:
            self.reconciler = KnowledgeReconciler(self.db, self.rag)

        # Bootstrap active context if missing in DB
        if not self.archetype_mgr.get_context(self.active_context_id):
            initial_dname = (
                "Arena Breakout: Infinite"
                if self.active_context_id in ("abi", "arena_breakout", "arena_breakout_infinite")
                else ("Game Advisor Universal" if self.active_context_id == "generic" else None)
            )
            self.scaffolder.bootstrap_context(
                context_id=self.active_context_id,
                display_name=initial_dname,
                activate=True,
            )

        self.metatuning = MetaTuningEngine(
            db=self.db,
            archetype_mgr=self.archetype_mgr,
            scaffolder=self.scaffolder,
            config=self.config,
            report_opener=self.report_opener,
        )

    @property
    def client(self) -> Any:
        return getattr(self.provider, "client", None)

    def _get_media_resolution(self) -> types.MediaResolution:
        res = (getattr(self.config.gemini, "media_resolution", "high") or "high").lower()
        if res == "high":
            return types.MediaResolution.MEDIA_RESOLUTION_HIGH
        if res == "medium":
            return types.MediaResolution.MEDIA_RESOLUTION_MEDIUM
        if res == "low":
            return types.MediaResolution.MEDIA_RESOLUTION_LOW
        return types.MediaResolution.MEDIA_RESOLUTION_HIGH

    def switch_context(
        self,
        new_context_id: str,
        new_display_name: Optional[str] = None,
        archetype_id: Optional[str] = None,
    ) -> TopicContext:
        """Switch active gaming topic context dynamically in RAM and DB without restart."""
        cid = new_context_id.strip().lower()
        if not cid:
            cid = "generic"

        ctx = self.archetype_mgr.get_context(cid)
        if ctx is None:
            ctx = self.scaffolder.bootstrap_context(
                context_id=cid,
                archetype_id=archetype_id,
                display_name=new_display_name,
                activate=True,
            )
        else:
            ctx = self.archetype_mgr.create_context(
                context_id=ctx.context_id,
                archetype_id=ctx.archetype_id,
                display_name=new_display_name or ctx.display_name,
                config=ctx.config,
                version=ctx.current_version,
                activate=True,
            )

        self.active_context_id = cid
        self.config.gemini.game = cid
        if self.memory:
            self.memory.default_game = cid
        if self.rag:
            self.rag.default_game = cid
            if hasattr(self.rag, "cache") and self.rag.cache:
                self.rag.cache.clear()

        # Update rolling history with a transition marker
        self.history.append(
            Turn(role="system", text=f"Contexto cambiado a {ctx.display_name} ({ctx.archetype_id}).")
        )

        # Render and display live dashboard on DISPLAY2
        arch = self.archetype_mgr.get_archetype(ctx.archetype_id)
        arch_title = arch.display_name if arch else ctx.archetype_id
        html_body = f"""
        <div class="card">
            <h2>🎮 Contexto Activo: {ctx.display_name}</h2>
            <div class="badge-row" style="margin-top: 10px; margin-bottom: 15px;">
                <span class="badge badge-purple">Arquetipo: {arch_title}</span>
                <span class="badge badge-blue">Contexto: {ctx.context_id}</span>
                <span class="badge badge-green">Estado: Conectado</span>
            </div>
            <p style="color: #9ca3af; line-height: 1.6;">
                El motor ha sincronizado las reglas tácticas de <strong>{ctx.display_name}</strong>, activado la memoria dinámica de arquetipo y purgado la caché L1 en RAM.
            </p>
        </div>
        """
        try:
            report_path = create_html_report(
                title=f"Dashboard: {ctx.display_name}",
                html_body=html_body,
                output_dir=self.config.reports.output_dir,
                auto_open=self.config.reports.auto_open_browser,
                opener=self.report_opener,
                preferred_browser=self.config.reports.preferred_browser,
                focus_browser=getattr(self.config.reports, "focus_browser", False),
            )
            self._last_report_path = str(report_path)
        except Exception:
            self._last_report_path = None

        return ctx

    def detect_context_switch_request(self, prompt: str) -> Optional[tuple[str, str]]:
        """Detect verbal requests to switch gaming context.

        Returns (context_id, display_name) or None.
        """
        p = prompt.strip().lower()

        patterns = [
            r"(?:vamos a jugar|vamos a darle a|juguemos a|jugar a)\s+([a-zA-Z0-9_\s:-]+)",
            r"(?:cambiar a|cambia a|cambiemos a|cambiar al juego|cambia al juego)\s+([a-zA-Z0-9_\s:-]+)",
            r"(?:cambiar contexto a|cambia contexto a|conmutar a)\s+([a-zA-Z0-9_\s:-]+)",
            r"(?:inicia contexto para|iniciar contexto para|inicia el contexto de)\s+([a-zA-Z0-9_\s:-]+)",
            r"(?:pon el juego|cargar juego|cambia de juego a)\s+([a-zA-Z0-9_\s:-]+)",
            r"(?:activar modo|cambia a modo|cambiar a modo|modo)\s+(advisor|gen[eé]rico|abi|coach)",
        ]

        for pat in patterns:
            m = re.search(pat, p, re.IGNORECASE)
            if m:
                raw_target = m.group(1).strip().strip(".?!,")
                if not raw_target:
                    continue
                clean_target = raw_target.lower()
                if any(x in clean_target for x in ("advisor", "generico", "genérico", "general", "universal")):
                    return ("generic", "Game Advisor Universal")
                if clean_target in ("abi", "arena breakout", "arena breakout infinite", "arena breakout: infinite", "coach"):
                    return ("abi", "Arena Breakout: Infinite")

                cid = re.sub(r"[^a-z0-9]+", "_", clean_target).strip("_")
                dname = raw_target.title()
                return (cid, dname)

        return None

    def get_system_instruction(self) -> str:
        """Retorna la instrucción de sistema adecuada según el preset de juego o personalización, enriquecida con memoria persistente."""
        game_id = self.active_context_id or getattr(self.config.gemini, "game", "generic")
        if self.config.gemini.system_instruction:
            base_prompt = self.config.gemini.system_instruction
        else:
            cur_file = Path(__file__).resolve()
            preset_path = None
            for p in cur_file.parents:
                cand = p / "presets" / f"{game_id}.md"
                if cand.is_file():
                    preset_path = cand
                    break

            if preset_path and preset_path.is_file():
                base_prompt = load_preset(game_id)
            elif game_id not in ("generic", ""):
                ctx = self.archetype_mgr.get_context(game_id)
                if ctx:
                    arch = self.archetype_mgr.get_archetype(ctx.archetype_id)
                    if arch and arch.default_system_prompt:
                        base_prompt = f"Eres un copiloto táctico para '{ctx.display_name}'.\n{arch.default_system_prompt}"
                    else:
                        base_prompt = load_preset(game_id)
                else:
                    base_prompt = load_preset(game_id)
            else:
                base_prompt = load_preset(game_id)

        if self.memory:
            profile_context = self.memory.format_profile_for_prompt(game=game_id)
            if profile_context:
                return f"{base_prompt}\n{profile_context}"

        return base_prompt

    def try_fast_path(self, prompt: str) -> Optional[CoachResponse]:
        """Attempt immediate zero-LLM local factual retrieval (< 2ms) for direct stat queries."""
        if not self.rag or not prompt:
            return None

        p_lower = prompt.lower().strip()
        stat_triggers = [
            "qué penetración", "que penetracion", "cuánta penetración", "cuanta penetracion",
            "cuánto daño", "cuanto dano", "cuánto de daño", "cuanto de dano",
            "qué daño", "que dano", "qué tier", "que tier", "de qué tier", "de que tier",
            "cuánto vale", "cuanto vale", "a cuánto se vende", "a cuanto se vende",
            "precio de", "estadísticas de", "estadisticas de", "stats de"
        ]

        if not any(trigger in p_lower for trigger in stat_triggers):
            return None

        # Search RAG with highest precision
        game_name = getattr(self.config.gemini, "game", "generic") or "generic"
        results = self.rag.search(prompt, game=game_name, limit=1)
        if not results:
            return None

        item = results[0]
        data = {}
        try:
            data = json.loads(item["data_json"])
        except Exception:
            pass

        title = item["title"]
        summary = item["summary"]

        if "penetration" in data and "damage" in data:
            tier_str = f", nivel Tier {data.get('tier', '?')}" if "tier" in data else ""
            spoken = f"La {title} tiene {data['penetration']} de penetración y {data['damage']} de daño base{tier_str}."
        elif "approx_value" in data:
            spoken = f"El {title} tiene un valor estimado de mercado de {data['approx_value']:,} Koens."
        else:
            spoken = summary

        # Append to history
        self.history.append(Turn(role="user", text=prompt))
        self.history.append(Turn(role="coach", text=spoken))

        return CoachResponse(
            spoken_text=spoken,
            report_path=None,
            input_tokens=0,
            output_tokens=0,
            latency_ms=1.5,
        )

    def ask(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
    ) -> CoachResponse:
        """Send multimodal or text query to LLM provider with tools and rolling history."""
        start_time = time.perf_counter()

        # Context switch check: conmutar juego o modo en caliente
        switch_info = self.detect_context_switch_request(prompt)
        if switch_info:
            cid, dname = switch_info
            ctx = self.switch_context(cid, dname)
            arch = self.archetype_mgr.get_archetype(ctx.archetype_id)
            arch_title = arch.display_name if arch else ctx.archetype_id
            spoken = (
                f"Cambié el contexto a {ctx.display_name}. "
                f"He activado el arquetipo de {arch_title} y sincronizado la memoria táctica. "
                f"Te abrí el nuevo panel en tu pantalla secundaria."
            )
            self.history.append(Turn(role="user", text=prompt))
            self.history.append(Turn(role="coach", text=spoken))
            return CoachResponse(
                spoken_text=spoken,
                report_path=self._last_report_path,
                input_tokens=0,
                output_tokens=0,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Meta-Tuning check: configuración global, persistencia de reglas y bucle de aclaración
        tuning_res = self.metatuning.process(prompt, self.active_context_id)
        if tuning_res:
            self.history.append(Turn(role="user", text=prompt))
            self.history.append(Turn(role="coach", text=tuning_res.spoken_response))
            return CoachResponse(
                spoken_text=tuning_res.spoken_response,
                report_path=tuning_res.report_path or self._last_report_path,
                input_tokens=0,
                output_tokens=0,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

        # Fast-Path check: resolve exact numerical facts locally in < 2ms without LLM latency
        if not image_bytes and not crop_bytes:
            fast_reply = self.try_fast_path(prompt)
            if fast_reply:
                return fast_reply

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

        # 1. Add rolling text history (without old images to save tokens)
        max_turns = max(0, getattr(self.config.history, "max_turns", 5))
        if max_turns > 0:
            entries_to_take = max_turns * 2
            history_slice = self.history[-entries_to_take:]
        else:
            history_slice = []

        history_lines = [f"{turn.role.upper()}: {turn.text}" for turn in history_slice]

        # 2. Add local tactical RAG facts if matching query (< 3ms FTS5 retrieval)
        if self.rag:
            game_name = getattr(self.config.gemini, "game", "generic") or "generic"
            rag_context = self.rag.format_context_for_prompt(prompt, game=game_name, limit=2)
            if rag_context:
                history_lines.append(rag_context)

        res = self.provider.generate(
            prompt=prompt,
            system_instruction=self.get_system_instruction(),
            image_bytes=image_bytes,
            crop_bytes=crop_bytes,
            history_text=history_lines,
            tool_callback=create_report_tool,
        )

        spoken_text = res.spoken_text or ""

        # Update history
        self.history.append(Turn(role="user", text=prompt))
        self.history.append(Turn(role="coach", text=spoken_text))
        if len(self.history) > 50:
            self.history = self.history[-50:]

        report_path = res.report_path or generated_report_path
        latency_ms = (
            res.latency_ms if res.latency_ms > 0 else (time.perf_counter() - start_time) * 1000
        )

        return CoachResponse(
            spoken_text=spoken_text,
            report_path=report_path,
            input_tokens=res.input_tokens,
            output_tokens=res.output_tokens,
            latency_ms=latency_ms,
        )
