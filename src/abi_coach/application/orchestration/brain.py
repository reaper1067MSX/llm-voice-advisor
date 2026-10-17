"""AI Brain facade delegating to AdvisorOrchestrator and GameContextSwitchUseCase."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from abi_coach.application.orchestration.advisor_orchestrator import AdvisorOrchestrator
from abi_coach.application.pipeline import ExceptionHandlingMiddleware, ExecutionPipeline, LoggingMiddleware
from abi_coach.application.services.context_factual_resolver import ContextFactualResolver
from abi_coach.application.services.history_manager import ConversationHistoryManager, Turn
from abi_coach.application.services.prompt_enricher import SystemPromptEnricherPipeline
from abi_coach.application.services.prompt_registry import (
    ABI_SYSTEM_INSTRUCTION,
    COACH_SYSTEM_INSTRUCTION,
    GENERIC_SYSTEM_INSTRUCTION,
    ONCE_HUMAN_SYSTEM_INSTRUCTION,
    PromptTemplateRegistry,
    load_preset,
)
from abi_coach.application.services.report_coordinator import TacticalReportToolCoordinator
from abi_coach.application.slices.archetypes.manager import ArchetypeManager, TopicContext
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.slices.companion_memory.memory import CompanionMemory
from abi_coach.application.slices.metatuning.engine import MetaTuningEngine
from abi_coach.application.slices.tactical_rag.rag import KnowledgeRAG
from abi_coach.application.slices.tactical_rag.reconciler import KnowledgeReconciler
from abi_coach.application.use_cases.context_switch import GameContextSwitchUseCase
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result, fail, ok
from abi_coach.domain.entities.interaction_records import CoachResponse, InteractionRequest, InteractionResult
from abi_coach.domain.ports.blackboard_port import BlackboardPort
from abi_coach.infrastructure.adapters.llm.base import LLMProvider
from abi_coach.infrastructure.adapters.llm.factory import create_llm_provider
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.adapters.storage.in_memory_blackboard import InMemoryBlackboard
from abi_coach.infrastructure.config.settings import AppConfig


class Brain:
    """Thin Facade orchestrating tactical advice, fast path queries, and context switches."""

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        report_opener: Optional[Callable[[str], Any]] = None,
        provider: Optional[LLMProvider] = None,
        memory: Optional[CompanionMemory] = None,
        rag: Optional[KnowledgeRAG] = None,
        reconciler: Optional[KnowledgeReconciler] = None,
        db: Optional[DatabaseManager] = None,
        blackboard: Optional[BlackboardPort] = None,
        fsm: Optional[Any] = None,
    ) -> None:
        from abi_coach.application.orchestration.fsm import TacticalFSM

        self.config, self.report_opener = config or AppConfig(), report_opener
        self.blackboard, self.fsm = blackboard or InMemoryBlackboard(), fsm or TacticalFSM()
        self._provider = provider or create_llm_provider(self.config)
        self.db = db or getattr(memory, "db", None) or getattr(rag, "db", None) or getattr(reconciler, "db", None) or DatabaseManager()
        self.archetype_mgr, self.scaffolder = ArchetypeManager(self.db), ArchetypeScaffolder(self.db, ArchetypeManager(self.db))
        self.active_context_id = getattr(self.config.gemini, "game", "generic") or "generic"
        self.memory = memory or CompanionMemory(self.db, default_game=self.active_context_id)
        self.rag = rag or KnowledgeRAG(self.db, default_game=self.active_context_id)
        self.reconciler = reconciler or KnowledgeReconciler(self.db, self.rag)

        if not self.archetype_mgr.get_context(self.active_context_id):
            dname = "Arena Breakout: Infinite" if self.active_context_id in ("abi", "arena_breakout", "arena_breakout_infinite") else ("Game Advisor Universal" if self.active_context_id == "generic" else None)
            self.scaffolder.bootstrap_context(context_id=self.active_context_id, display_name=dname, activate=True)

        self.metatuning = MetaTuningEngine(db=self.db, archetype_mgr=self.archetype_mgr, scaffolder=self.scaffolder, config=self.config, report_opener=self.report_opener)
        self.pipeline = ExecutionPipeline([ExceptionHandlingMiddleware(), LoggingMiddleware()])
        self._prompt_registry, self._history_mgr = PromptTemplateRegistry(), ConversationHistoryManager(50)
        self._prompt_pipeline = SystemPromptEnricherPipeline(self._prompt_registry)
        self.history: List[Turn] = self._history_mgr._turns
        rep = getattr(self.config, "reports", None)
        self._report_coordinator = TacticalReportToolCoordinator(
            output_dir=getattr(rep, "output_dir", None), auto_open=getattr(rep, "auto_open_browser", True),
            opener=self.report_opener, preferred_browser=getattr(rep, "preferred_browser", None),
            focus_browser=getattr(rep, "focus_browser", False),
        )
        self._context_switch = GameContextSwitchUseCase(
            archetype_mgr=self.archetype_mgr, scaffolder=self.scaffolder,
            report_coordinator=self._report_coordinator, history_mgr=self._history_mgr,
            config=self.config, memory=self.memory, rag=self.rag,
        )
        self._factual_resolver = ContextFactualResolver(rag=self.rag, archetype_mgr=self.archetype_mgr)
        self._orchestrator = AdvisorOrchestrator(
            provider=self._provider, prompt_pipeline=self._prompt_pipeline, history_mgr=self._history_mgr,
            report_coordinator=self._report_coordinator, factual_resolver=self._factual_resolver,
            context_switch_use_case=self._context_switch, fsm=self.fsm, blackboard=self.blackboard,
            metatuning=self.metatuning, rag=self.rag, archetype_mgr=self.archetype_mgr,
            memory=self.memory, config=self.config,
        )

    @property
    def provider(self) -> Any:
        if hasattr(self, "_orchestrator") and self._orchestrator is not None:
            return self._orchestrator.provider
        return getattr(self, "_provider", None)

    @provider.setter
    def provider(self, val: Any) -> None:
        self._provider = val
        if hasattr(self, "_orchestrator") and self._orchestrator is not None:
            self._orchestrator.provider = val

    @property
    def client(self) -> Any: return getattr(self.provider, "client", None)


    @property
    def _last_report_path(self) -> Optional[str]: return self._report_coordinator.last_report_path

    @_last_report_path.setter
    def _last_report_path(self, val: Optional[str]) -> None: self._report_coordinator.last_report_path = val

    @property
    def current_game(self) -> str: return self.active_context_id

    @current_game.setter
    def current_game(self, val: str) -> None: self.active_context_id = val

    def switch_context(self, new_context_id: str, new_display_name: Optional[str] = None, archetype_id: Optional[str] = None) -> TopicContext:
        ctx = self._context_switch.execute(new_context_id, new_display_name, archetype_id)
        self.active_context_id = ctx.context_id
        return ctx

    def detect_context_switch_request(self, prompt: str) -> Optional[tuple[str, str]]:
        return self._context_switch.detect_request(prompt)

    def get_system_instruction(self) -> str:
        return self._prompt_pipeline.build_system_instruction(
            game_id=self.active_context_id, custom_instruction=getattr(getattr(self.config, "gemini", None), "system_instruction", None),
            archetype_mgr=self.archetype_mgr, memory=self.memory,
        )

    def try_fast_path(self, prompt: str) -> Optional[CoachResponse]:
        spoken = self._factual_resolver.try_resolve_factual(prompt, self.active_context_id)
        if not spoken:
            return None
        self._history_mgr.add_user_coach(prompt, spoken)
        return CoachResponse(spoken_text=spoken, latency_ms=1.5)

    def ask(self, prompt: str, image_bytes: Optional[bytes] = None, crop_bytes: Optional[Dict[str, bytes]] = None, screenshot: Optional[bytes] = None, **kwargs: Any) -> CoachResponse:
        req = InteractionRequest(prompt=prompt, image_bytes=image_bytes or screenshot, crop_bytes=crop_bytes, context_id=self.active_context_id)
        res = self._orchestrator.execute(req)
        self.active_context_id = getattr(self.config.gemini, "game", self.active_context_id)
        return res

    def ask_result(self, prompt: str, image_bytes: Optional[bytes] = None, crop_bytes: Optional[Dict[str, bytes]] = None, screenshot: Optional[bytes] = None, **kwargs: Any) -> Result[CoachResponse, DomainError]:
        @dataclass(frozen=True)
        class _Cmd: prompt: str; img: Optional[bytes]; crop: Optional[Dict[str, bytes]]
        def _h(cmd: _Cmd) -> Result[CoachResponse, DomainError]:
            try: return ok(self.ask(prompt=cmd.prompt, image_bytes=cmd.img, crop_bytes=cmd.crop))
            except Exception as exc:
                err = getattr(exc, "_domain_error", None)
                if isinstance(err, DomainError): return fail(err)
                raise
        return self.pipeline.execute(_Cmd(prompt, image_bytes or screenshot, crop_bytes), _h)
