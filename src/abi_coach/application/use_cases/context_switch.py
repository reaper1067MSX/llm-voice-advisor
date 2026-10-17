"""Game context switching use case and state synchronization."""

from __future__ import annotations

from typing import Any, Optional

from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.application.services.report_coordinator import TacticalReportToolCoordinator
from abi_coach.application.slices.archetypes.manager import ArchetypeManager, TopicContext
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.use_cases.context_switch_detector import ContextSwitchDetector
from abi_coach.domain.entities.interaction_records import CoachResponse


class GameContextSwitchUseCase:
    """Orchestrates gaming context transitions, preset reloading, and state synchronization."""

    def __init__(
        self,
        archetype_mgr: ArchetypeManager,
        scaffolder: ArchetypeScaffolder,
        report_coordinator: Optional[TacticalReportToolCoordinator] = None,
        history_mgr: Optional[ConversationHistoryManager] = None,
        config: Optional[Any] = None,
        memory: Optional[Any] = None,
        rag: Optional[Any] = None,
        detector: Optional[ContextSwitchDetector] = None,
    ) -> None:
        self.archetype_mgr = archetype_mgr
        self.scaffolder = scaffolder
        self.report_coordinator = report_coordinator
        self.history_mgr = history_mgr
        self.config = config
        self.memory = memory
        self.rag = rag
        self.detector = detector or ContextSwitchDetector()

    def detect_request(self, prompt: str) -> Optional[tuple[str, str]]:
        """Detect context switch trigger and return (target_game, display_name)."""
        req = self.detector.detect(prompt)
        if not req:
            return None
        return (req.target_game, req.display_name)

    def execute(
        self,
        new_context_id: str,
        new_display_name: Optional[str] = None,
        archetype_id: Optional[str] = None,
    ) -> TopicContext:
        """Switch active game context and synchronize all application components."""
        cid = (new_context_id or "").strip().lower() or "generic"
        ctx = self.archetype_mgr.get_context(cid)
        if ctx is None:
            ctx = self.scaffolder.bootstrap_context(
                cid, archetype_id=archetype_id, display_name=new_display_name, activate=True
            )
        else:
            ctx = self.archetype_mgr.create_context(
                ctx.context_id,
                archetype_id=ctx.archetype_id,
                display_name=new_display_name or ctx.display_name,
                config=ctx.config,
                version=ctx.current_version,
                activate=True,
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
        """Detect and execute verbal context switch immediately without LLM latency."""
        req = self.detector.detect(prompt)
        if not req:
            return None
        ctx = self.execute(req.target_game, req.display_name, req.archetype_id)
        arch = self.archetype_mgr.get_archetype(ctx.archetype_id)
        arch_title = arch.display_name if arch else ctx.archetype_id
        spoken = (
            f"Cambié el contexto a {ctx.display_name}. He activado el arquetipo de {arch_title} "
            f"y sincronizado la memoria táctica. Te abrí el nuevo panel en tu pantalla secundaria."
        )
        if self.history_mgr is not None:
            self.history_mgr.add_user_coach(prompt, spoken)
        last_rep = self.report_coordinator.last_report_path if self.report_coordinator else None
        return CoachResponse(
            spoken_text=spoken,
            report_path=last_rep,
            input_tokens=0,
            output_tokens=0,
            latency_ms=0.0,
        )
