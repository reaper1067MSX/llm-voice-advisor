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

from abi_coach.application.orchestration.fsm import TacticalFSM
from abi_coach.application.pipeline.exception_middleware import ExceptionHandlingMiddleware
from abi_coach.application.pipeline.execution_pipeline import ExecutionPipeline
from abi_coach.application.pipeline.logging_middleware import LoggingMiddleware
from abi_coach.application.slices.archetypes.manager import ArchetypeManager, TopicContext
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.slices.companion_memory.memory import CompanionMemory, MemoryItem
from abi_coach.application.slices.metatuning.engine import MetaTuningEngine, MetaTuningResult
from abi_coach.application.slices.reporting.reports import create_html_report
from abi_coach.application.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG
from abi_coach.application.slices.tactical_rag.reconciler import KnowledgeReconciler, ReconciliationDiff
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Failure, Result, Success, fail, ok
from abi_coach.domain.entities.tactical_state import GameStateContext, TacticalState
from abi_coach.domain.ports.blackboard_port import BlackboardPort
from abi_coach.infrastructure.adapters.llm.base import LLMProvider
from abi_coach.infrastructure.adapters.llm.factory import create_llm_provider
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.adapters.storage.in_memory_blackboard import InMemoryBlackboard
from abi_coach.infrastructure.config.settings import AppConfig


ABI_SYSTEM_INSTRUCTION = """Eres 'ABI Coach', un copiloto táctico y compañero de escuadrón (Squadmate) de élite para el videojuego 'Arena Breakout: Infinite' (PC).
Estás hablando directamente con el jugador a través de su auricular mientras juega a 1440p con un monitor secundario dedicado a visualización de datos tácticos.

PERFIL Y PERSONALIDAD (SQUADMATE):
- Eres su compañero de confianza en la zona oscura de Kamona: leal, analítico, directo y motivador.
- Conoces el meta actual y la dura realidad económica tras el regreso de la Temporada 3 (S3) a la Temporada 7 (S7).
- Hablas con jerga táctica gamer de extracción (alijo, Koens, contratos de Deke, tier de balas, penetración, TTK, leg meta).
- Respetas el audio del juego: si el jugador está en combate o en sigilo, aplicas disciplina de radio estricta.

REGLAS DE RESPUESTA:
1. Formato de Voz (TTS):
   - Responde SIEMPRE en español, en un tono natural, cercano, profesional y ágil.
   - Sé breve por voz: 1 a 3 oraciones como máximo para no tapar los pasos de los enemigos.
   - NUNCA uses formato markdown en tu texto hablado (nada de asteriscos, numerales, viñetas o tablas de texto). Habla de forma fluida con pausas naturales.

2. USO DE REPORTES VISUALES Y GRÁFICOS (create_html_report):
   - **ESTRICTAMENTE BAJO DEMANDA**: NUNCA invoques la herramienta de reporte por iniciativa propia en preguntas directas o consejos rápidos.
   - **SOLO** debes invocar la herramienta 'create_html_report' si el jugador lo pide de forma EXPLÍCITA (ejemplos: "abre un reporte", "hazme una tabla", "muéstrame un gráfico de daño", "compara los precios en pantalla").
   - ESTRUCTURA DEL HTML (cuando sea pedido):
     * Una card con tabla estilizada (<table>) con columnas útiles (Objeto, Tier, Penetración / Daño, Costo Koens, Veredicto). Insignias de colores por tier.
     * Un gráfico interactivo Chart.js contenido y bien dimensionado (max-height: 280px).
   - En tu respuesta de voz, da el consejo clave y añade: "Te abrí la tabla y el gráfico en tu pantalla secundaria para que veas los números exactos."

3. CONOCIMIENTO TÁCTICO DE ABI:
   - Regla de oro: la munición define la penetración y el TTK, no el arma.
   - Economía: prioriza valor por casilla (Purple/Gold de 1 slot), contratos diarios de Deke Vinson, y kits de bajo riesgo (MP5 Dum-Dum a piernas o Mosin con LPS/SNB).
   - Honestidad estricta: Si no distingues claramente un objeto en pantalla, dilo honestamente en vez de inventar números.
   - Disciplina de radio: En situaciones de combate o tiroteo tenso, da solo información vital en pocas palabras.
"""

GENERIC_SYSTEM_INSTRUCTION = """Eres 'Game Advisor', un copiloto táctico y compañero de escuadrón (Squadmate) con Inteligencia Artificial multimodal para PC en tiempo real.
Estás hablando directamente con el jugador a través de su auricular mientras juega en su monitor principal con una pantalla secundaria dedicada a dashboards y visualización de datos.

TU ROL Y PERSONALIDAD (SQUADMATE):
- Eres el compañero de escuadrón definitivo: leal, atento, proactivo y analítico.
- Hablas con jerga gamer y militar táctica natural (loot, alijo, push, trade, hold, TTK, rotación).
- Observas la pantalla y entiendes el ritmo de la partida: cuando hay calma compartes observaciones estratégicas útiles; cuando hay acción mantienes disciplina de radio.
- NUNCA inventes información. Si no distingues claramente un texto o detalle en pantalla, dilo con honestidad.

REGLAS DE RESPUESTA:
1. Formato de Voz (TTS):
   - Responde SIEMPRE en español, con tono natural, cercano, ágil y motivador.
   - Sé breve y conciso por voz: 1 a 3 oraciones como máximo para no entorpecer el audio del juego.
   - NUNCA uses formato markdown en tu texto hablado (nada de asteriscos, numerales, viñetas o tablas). Habla de forma fluida con pausas naturales.

2. USO DE REPORTES Y GRÁFICOS VISUALES (create_html_report):
   - **ESTRICTAMENTE BAJO DEMANDA**: NUNCA generes reportes HTML en conversaciones casuales, respuestas rápidas o preguntas de sí/no.
   - **SOLO** debes invocar la herramienta 'create_html_report' cuando el jugador pida EXPLÍCITAMENTE una visualización (ejemplos: "abre un reporte", "muéstrame una tabla", "hazme un gráfico", "compara los números en pantalla", "desglosa las estadísticas").
   - ESTRUCTURA DEL HTML (cuando sea explícitamente pedido):
     * Una card con tabla estilizada (<table>) con columnas claras y badges de colores.
     * Un gráfico interactivo Chart.js contenido y bien dimensionado (max-height: 280px).
   - En tu respuesta de voz cuando generes un reporte, resume la conclusión en una frase y añade: "Te abrí la tabla y el gráfico en tu pantalla secundaria."

3. DISCIPLINA DE RADIO Y MODOS DE CONCENTRACIÓN:
   - Si detectas combate intenso o peligro inminente, reduce tus respuestas a advertencias vitales directas de menos de 5 palabras.
   - Si el jugador te pide silencio de radio o modo concentración, respeta la orden inmediatamente.
"""

# Alias para compatibilidad previa
COACH_SYSTEM_INSTRUCTION = ABI_SYSTEM_INSTRUCTION

ONCE_HUMAN_SYSTEM_INSTRUCTION = """Eres 'Once Human Companion', un copiloto táctico y compañero de supervivencia (Metahumano / Mayfly) experto en 'Once Human' (PC).
Estás hablando directamente con el jugador a través de su auricular mientras juega a 1440p con un monitor secundario para dashboards tácticos.

TU ROL Y PERSONALIDAD (SQUADMATE METAHUMANO):
- Eres su compañero de clan leal, analítico y directo en el mundo post-apocalíptico de Nalcott.
- Dominas a la perfección la teoría y práctica de builds meta (Shrapnel, Unstable Bomber, Power Surge, Burn, Frost Vortex, Bounce, Fortress Warfare).
- Conoces la fórmula 1-4-1 para builds de crítico (1 Key Armor como Shaman Vulture Top o Gas-Tight Helmet + 4 Lonewolf + 1 Bastille Boots).
- Conoces los sufijos estrictos de mods: <Violent> para builds de Crítico/Daño Crítico, y <Talent> para daño de estado/elemental.
- Asesoras con precisión en la rotación de combate, aplicación de marcas (The Bull's Eye con sniper Bingo o arco Recurve), gestión de Starchrom (Astrocromita en la Wish Machine) y farmeo en Silos de Contención (PHI, PSI, SIGMA, THETA, EX1) y Monolitos de jefes.

REGLAS DE RESPUESTA:
1. Formato de Voz (TTS):
   - Responde SIEMPRE en español, con tono natural, cercano, ágil y motivador.
   - Sé breve y conciso por voz: 1 a 3 oraciones como máximo para no tapar el audio del juego o las alertas de Deviations.
   - NUNCA uses formato markdown en tu texto hablado (nada de asteriscos, numerales, viñetas o tablas). Habla de forma fluida con pausas naturales.

2. USO DE REPORTES Y GRÁFICOS VISUALES (create_html_report):
   - **ESTRICTAMENTE BAJO DEMANDA**: NUNCA generes reportes HTML en conversaciones casuales o consejos rápidos de combate.
   - **SOLO** debes invocar la herramienta 'create_html_report' cuando el jugador pida EXPLÍCITAMENTE una visualización (ejemplos: "abre un reporte", "muéstrame la tabla de build", "hazme un gráfico de daño", "compara los sets de armadura en pantalla", "desglosa dónde farmear los mods").
   - ESTRUCTURA DEL HTML (cuando sea pedido):
     * Una card con tabla estilizada (<table>) con columnas claras: Pieza, Mod BiS (Mejor en Ranura), Sufijo (<Violent>/<Talent>), Silo de Farmeo, Efecto.
     * Un gráfico interactivo Chart.js contenido y bien dimensionado (max-height: 280px).
   - En tu respuesta de voz, resume el consejo clave en dos oraciones y añade: "Te abrí la tabla de build y detalles en tu pantalla secundaria."

3. DISCIPLINA DE RADIO Y MODOS DE CONCENTRACIÓN:
   - Si detectas combate intenso (Prime War, Monolito de Jefe, Silo pesadilla), mantén disciplina de radio: solo avisos vitales ultra-concisos (<5 palabras).
   - Si el jugador te pide silencio de radio o modo concentración, respeta la orden inmediatamente.
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
    provider_name: str = "gemini"


_PRESET_CACHE: Dict[str, str] = {}


def load_preset(game_name: str) -> str:
    """Load game system instruction markdown from presets directory with in-memory cache."""
    clean_name = (game_name or "").lower().strip()
    if clean_name in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
        canonical = "abi"
    elif clean_name in ("once_human", "oncehuman", "once-human", "once human"):
        canonical = "once_human"
    elif clean_name:
        canonical = re.sub(r"[^a-z0-9]+", "_", clean_name).strip("_")
    else:
        canonical = "generic"

    if canonical in _PRESET_CACHE:
        return _PRESET_CACHE[canonical]

    import sys

    # Search for presets directory across base_dir, _MEIPASS, and parent directories
    preset_candidates = []
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        preset_candidates.append(base / "presets" / f"{canonical}.md")
        preset_candidates.append(base / "presets" / f"{clean_name}.md")
        if hasattr(sys, "_MEIPASS"):
            preset_candidates.append(Path(sys._MEIPASS) / "presets" / f"{canonical}.md")
            preset_candidates.append(Path(sys._MEIPASS) / "presets" / f"{clean_name}.md")

    cur_file = Path(__file__).resolve()
    for p in cur_file.parents:
        preset_candidates.append(p / "presets" / f"{canonical}.md")
        preset_candidates.append(p / "presets" / f"{clean_name}.md")
        preset_candidates.append(p / "infrastructure" / "resources" / "presets" / f"{canonical}.md")
        preset_candidates.append(p / "infrastructure" / "resources" / "presets" / f"{clean_name}.md")
        preset_candidates.append(
            p / "src" / "abi_coach" / "infrastructure" / "resources" / "presets" / f"{canonical}.md"
        )
        preset_candidates.append(
            p / "src" / "abi_coach" / "infrastructure" / "resources" / "presets" / f"{clean_name}.md"
        )

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

    if canonical == "abi":
        fallback = ABI_SYSTEM_INSTRUCTION
    elif canonical == "once_human":
        fallback = ONCE_HUMAN_SYSTEM_INSTRUCTION
    else:
        fallback = GENERIC_SYSTEM_INSTRUCTION

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
        blackboard: Optional[BlackboardPort] = None,
        fsm: Optional[TacticalFSM] = None,
    ):
        self.config = config
        self.report_opener = report_opener
        self.history: List[Turn] = []
        self.blackboard: BlackboardPort = blackboard or InMemoryBlackboard()
        self.fsm: TacticalFSM = fsm or TacticalFSM()

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
        self.pipeline = ExecutionPipeline(
            [ExceptionHandlingMiddleware(), LoggingMiddleware()]
        )

    @property
    def client(self) -> Any:
        return getattr(self.provider, "client", None)

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
                if any(x in clean_target for x in ("once human", "oncehuman", "once-human", "once_human")):
                    return ("once_human", "Once Human")

                cid = re.sub(r"[^a-z0-9]+", "_", clean_target).strip("_")
                dname = raw_target.title()
                return (cid, dname)

        return None

    def get_system_instruction(self) -> str:
        """Retorna la instrucción de sistema adecuada según el preset de juego o personalización, enriquecida con memoria persistente."""
        game_id = self.active_context_id or getattr(self.config.gemini, "game", "generic") or "generic"
        if self.config.gemini.system_instruction:
            base_prompt = self.config.gemini.system_instruction
        else:
            cur_file = Path(__file__).resolve()
            preset_path = None
            for p in cur_file.parents:
                for cand in (
                    p / "presets" / f"{game_id}.md",
                    p / "infrastructure" / "resources" / "presets" / f"{game_id}.md",
                    p / "src" / "abi_coach" / "infrastructure" / "resources" / "presets" / f"{game_id}.md",
                ):
                    if cand.is_file():
                        preset_path = cand
                        break
                if preset_path:
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

        enrichments: List[str] = []
        if self.memory:
            profile_context = self.memory.format_profile_for_prompt(game=game_id)
            if profile_context:
                enrichments.append(profile_context)
        if self.archetype_mgr:
            engram_context = self.archetype_mgr.format_profile_for_prompt(context_id=game_id)
            if engram_context:
                enrichments.append(engram_context)

        if enrichments:
            return f"{base_prompt}\n" + "\n".join(enrichments)

        return base_prompt

    def try_fast_path(self, prompt: str) -> Optional[CoachResponse]:
        """Attempt immediate zero-LLM local factual retrieval (< 2ms) for direct stat queries."""
        if (not self.rag and not self.archetype_mgr) or not prompt:
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

        def _extract_stats(entry: Dict[str, Any]) -> Dict[str, Any]:
            if "data_json" in entry and entry["data_json"]:
                try:
                    return json.loads(entry["data_json"])
                except Exception:
                    return {}
            if "facets" in entry and isinstance(entry["facets"], dict):
                return entry["facets"]
            if "facets_json" in entry and entry["facets_json"]:
                try:
                    return json.loads(entry["facets_json"])
                except Exception:
                    return {}
            return {}

        game_id = self.active_context_id or getattr(self.config.gemini, "game", "generic") or "generic"
        results = self.rag.search(prompt, game=game_id, limit=2) if self.rag else []

        generic_words = {
            "que", "qué", "cual", "cuál", "cuanto", "cuánto", "cuanta", "cuánta",
            "tiene", "tienen", "es", "son", "de", "la", "el", "los", "las", "un", "una",
            "penetracion", "penetración", "dano", "daño", "tier", "nivel", "vale",
            "vende", "precio", "estadisticas", "estadísticas", "stats", "base",
            "bala", "balas", "municion", "munición", "arma", "rifle", "objeto",
        }
        query_words = [
            w.lower()
            for w in re.findall(r"[A-Za-z0-9_\-\.]+", prompt)
            if len(w) > 1 and w.lower() not in generic_words
        ]

        def _matches_query_entity(entry: Dict[str, Any]) -> bool:
            if not query_words:
                return True
            haystack = f"{entry.get('title', '')} {entry.get('entity_key', '')}".lower()
            return any(qw in haystack for qw in query_words)

        item: Optional[Dict[str, Any]] = None
        data: Dict[str, Any] = {}
        for r in results:
            if not _matches_query_entity(r):
                continue
            d = _extract_stats(r)
            if ("penetration" in d and "damage" in d) or "approx_value" in d:
                item = r
                data = d
                break

        if item is None and self.archetype_mgr:
            v2_results = self.archetype_mgr.search_entities(prompt, context_id=game_id, limit=2)
            for r in v2_results:
                if not _matches_query_entity(r):
                    continue
                d = _extract_stats(r)
                if ("penetration" in d and "damage" in d) or "approx_value" in d:
                    item = r
                    data = d
                    break
            if item is None:
                for r in v2_results:
                    if _matches_query_entity(r):
                        item = r
                        data = _extract_stats(item)
                        break

        if item is None:
            for r in results:
                if _matches_query_entity(r):
                    item = r
                    data = _extract_stats(item)
                    break

        if item is None:
            return None

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

        # 0. Voice silence & focus mode command interception (sub-millisecond instant response)
        silence_reply = self.fsm.intercept_voice_command(prompt)
        if silence_reply:
            self.blackboard.set_tactical_state(self.fsm.state)
            self.history.append(Turn(role="user", text=prompt))
            self.history.append(Turn(role="coach", text=silence_reply))
            return CoachResponse(
                spoken_text=silence_reply,
                report_path=self._last_report_path,
                input_tokens=0,
                output_tokens=0,
                latency_ms=(time.perf_counter() - start_time) * 1000,
            )

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

        # 2. Add local tactical RAG facts (v1 game_knowledge + v2 topic_entities)
        game_name = self.active_context_id or getattr(self.config.gemini, "game", "generic") or "generic"
        if self.rag:
            rag_context = self.rag.format_context_for_prompt(prompt, game=game_name, limit=2)
            if rag_context:
                history_lines.append(rag_context)
        if self.archetype_mgr:
            v2_rag_context = self.archetype_mgr.format_rag_for_prompt(prompt, context_id=game_name, limit=2)
            if v2_rag_context:
                history_lines.append(v2_rag_context)

        # 3. Add active blackboard tactical state if relevant
        bb_state = self.blackboard.get_state()
        if bb_state.screen_summary:
            history_lines.append(f"[ESTADO VISUAL EN MEMORIA]: {bb_state.screen_summary}")
        if bb_state.state != TacticalState.EXPLORING:
            history_lines.append(f"[ESTADO TÁCTICO ACTUAL]: {bb_state.state.value.upper()}")

        raw_res = self.provider.generate(
            prompt=prompt,
            system_instruction=self.get_system_instruction(),
            image_bytes=image_bytes,
            crop_bytes=crop_bytes,
            history_text=history_lines,
            tool_callback=create_report_tool,
        )

        # Support both hexagonal Result[LLMResponseDTO, ProviderError] and legacy ProviderResponse
        if isinstance(raw_res, Failure):
            err = raw_res.error
            exc = RuntimeError(getattr(err, "message", str(err)))
            exc._domain_error = err  # type: ignore[attr-defined]
            raise exc
        elif isinstance(raw_res, Success):
            dto = raw_res.unwrap()
            spoken_text = dto.spoken_text or ""
            in_tokens = dto.tokens.input_tokens
            out_tokens = dto.tokens.output_tokens
            res_report_path = generated_report_path
            res_latency = dto.latency_ms
            provider_name = getattr(dto, "provider_name", "gemini")
        else:
            spoken_text = raw_res.spoken_text or ""
            in_tokens = raw_res.input_tokens
            out_tokens = raw_res.output_tokens
            res_report_path = raw_res.report_path or generated_report_path
            res_latency = raw_res.latency_ms
            provider_name = getattr(raw_res, "provider_name", "gemini")

        # Update history
        self.history.append(Turn(role="user", text=prompt))
        self.history.append(Turn(role="coach", text=spoken_text))
        if len(self.history) > 50:
            self.history = self.history[-50:]

        latency_ms = (
            res_latency if res_latency > 0 else (time.perf_counter() - start_time) * 1000
        )

        return CoachResponse(
            spoken_text=spoken_text,
            report_path=res_report_path,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_ms=latency_ms,
            provider_name=provider_name,
        )

    def ask_result(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
    ) -> Result[CoachResponse, DomainError]:
        """Execute tactical query through Clean Architecture ExecutionPipeline returning Result[CoachResponse, DomainError]."""
        @dataclass(frozen=True)
        class _AskQueryCommand:
            prompt: str
            image_bytes: Optional[bytes] = None
            crop_bytes: Optional[Dict[str, bytes]] = None

        def _handler(cmd: _AskQueryCommand) -> Result[CoachResponse, DomainError]:
            try:
                resp = self.ask(
                    prompt=cmd.prompt,
                    image_bytes=cmd.image_bytes,
                    crop_bytes=cmd.crop_bytes,
                )
                return ok(resp)
            except Exception as exc:
                domain_err = getattr(exc, "_domain_error", None)
                if isinstance(domain_err, DomainError):
                    return fail(domain_err)
                raise

        return self.pipeline.execute(
            _AskQueryCommand(prompt=prompt, image_bytes=image_bytes, crop_bytes=crop_bytes),
            _handler,
        )

