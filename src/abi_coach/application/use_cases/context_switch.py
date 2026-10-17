"""Game context switching use case and verbal detection."""
from __future__ import annotations
import re
from typing import Any, Optional
from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.application.services.report_coordinator import TacticalReportToolCoordinator
from abi_coach.application.slices.archetypes.manager import ArchetypeManager, TopicContext
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.use_cases import CoachResponse

CONTEXT_PATTERNS = [
    r"(?:vamos a jugar|vamos a darle a|juguemos a|jugar a)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:cambiar a|cambia a|cambiemos a|cambiar al juego|cambia al juego)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:cambiar contexto a|cambia contexto a|conmutar a)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:inicia contexto para|iniciar contexto para|inicia el contexto de)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:pon el juego|cargar juego|cambia de juego a)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:activar modo|cambia a modo|cambiar a modo|modo)\s+(advisor|gen[eé]rico|abi|coach)",
]

class GameContextSwitchUseCase:
    """Handles gaming context transitions, preset reloading, and state synchronization."""

    def __init__(
        self, archetype_mgr: ArchetypeManager, scaffolder: ArchetypeScaffolder,
        report_coordinator: Optional[TacticalReportToolCoordinator] = None,
        history_mgr: Optional[ConversationHistoryManager] = None,
        config: Optional[Any] = None, memory: Optional[Any] = None, rag: Optional[Any] = None,
    ) -> None:
        self.archetype_mgr, self.scaffolder = archetype_mgr, scaffolder
        self.report_coordinator, self.history_mgr = report_coordinator, history_mgr
        self.config, self.memory, self.rag = config, memory, rag

    def detect_request(self, prompt: str) -> Optional[tuple[str, str]]:
        p = prompt.strip().lower()
        for pat in CONTEXT_PATTERNS:
            m = re.search(pat, p, re.IGNORECASE)
            if m:
                raw = m.group(1).strip().strip(".?!,")
                if not raw:
                    continue
                cl = raw.lower()
                if any(x in cl for x in ("advisor", "generico", "genérico", "general", "universal")):
                    return ("generic", "Game Advisor Universal")
                if cl in ("abi", "arena breakout", "arena breakout infinite", "arena breakout: infinite", "coach"):
                    return ("abi", "Arena Breakout: Infinite")
                if any(x in cl for x in ("once human", "oncehuman", "once-human", "once_human")):
                    return ("once_human", "Once Human")
                return (re.sub(r"[^a-z0-9]+", "_", cl).strip("_"), raw.title())
        return None

    def execute(self, new_context_id: str, new_display_name: Optional[str] = None, archetype_id: Optional[str] = None) -> TopicContext:
        cid = (new_context_id or "").strip().lower() or "generic"
        ctx = self.archetype_mgr.get_context(cid)
        if ctx is None:
            ctx = self.scaffolder.bootstrap_context(cid, archetype_id=archetype_id, display_name=new_display_name, activate=True)
        else:
            ctx = self.archetype_mgr.create_context(
                ctx.context_id, archetype_id=ctx.archetype_id, display_name=new_display_name or ctx.display_name,
                config=ctx.config, version=ctx.current_version, activate=True,
            )
        if self.config and hasattr(self.config, "gemini"):
            self.config.gemini.game = cid
        if self.memory and hasattr(self.memory, "default_game"):
            self.memory.default_game = cid
        if self.rag and hasattr(self.rag, "default_game"):
            self.rag.default_game = cid
            if getattr(self.rag, "cache", None):
                self.rag.cache.clear()
        if self.history_mgr is not None:
            self.history_mgr.add_turn("system", f"Contexto cambiado a {ctx.display_name} ({ctx.archetype_id}).")
        if self.report_coordinator:
            arch = self.archetype_mgr.get_archetype(ctx.archetype_id)
            self.report_coordinator.render_context_dashboard(
                ctx.context_id, ctx.display_name, arch.display_name if arch else ctx.archetype_id
            )
        return ctx

    def handle_verbal_switch(self, prompt: str) -> Optional[CoachResponse]:
        info = self.detect_request(prompt)
        if not info:
            return None
        ctx = self.execute(info[0], info[1])
        arch = self.archetype_mgr.get_archetype(ctx.archetype_id)
        arch_title = arch.display_name if arch else ctx.archetype_id
        spoken = f"Cambié el contexto a {ctx.display_name}. He activado el arquetipo de {arch_title} y sincronizado la memoria táctica. Te abrí el nuevo panel en tu pantalla secundaria."
        if self.history_mgr is not None:
            self.history_mgr.add_user_coach(prompt, spoken)
        last_rep = self.report_coordinator.last_report_path if self.report_coordinator else None
        return CoachResponse(spoken_text=spoken, report_path=last_rep, input_tokens=0, output_tokens=0, latency_ms=0.0)
