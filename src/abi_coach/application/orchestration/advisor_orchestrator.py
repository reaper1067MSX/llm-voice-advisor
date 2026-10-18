"""Generic Advisor Process Orchestrator unifiying deterministic fast path and multimodal LLM."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, List, Optional

from abi_coach.application.pipeline import ExceptionHandlingMiddleware, ExecutionPipeline, LoggingMiddleware
from abi_coach.application.services.context_factual_resolver import ContextFactualResolver
from abi_coach.application.services.history_manager import ConversationHistoryManager, Turn
from abi_coach.application.services.prompt_enricher import SystemPromptEnricherPipeline
from abi_coach.application.services.prompt_registry import PromptTemplateRegistry
from abi_coach.application.services.report_coordinator import TacticalReportToolCoordinator
from abi_coach.application.slices.archetypes.manager import ArchetypeManager, TopicContext
from abi_coach.application.slices.archetypes.scaffolder import ArchetypeScaffolder
from abi_coach.application.slices.companion_memory.memory import CompanionMemory
from abi_coach.application.slices.metatuning.engine import MetaTuningEngine
from abi_coach.application.slices.tactical_rag.rag import KnowledgeRAG
from abi_coach.application.slices.tactical_rag.reconciler import KnowledgeReconciler
from abi_coach.application.use_cases.context_switch import GameContextSwitchUseCase
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Failure, Result, Success, fail, ok
from abi_coach.domain.entities.interaction_records import InteractionRequest, InteractionResult
from abi_coach.domain.entities.tactical_state import TacticalState
from abi_coach.domain.ports.blackboard_port import BlackboardPort
from abi_coach.infrastructure.adapters.llm.base import LLMProvider
from abi_coach.infrastructure.adapters.llm.factory import create_llm_provider
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager
from abi_coach.infrastructure.adapters.storage.in_memory_blackboard import InMemoryBlackboard
from abi_coach.infrastructure.config.settings import AppConfig


@dataclass
class AdvisorServices:
    """Parameter Object encapsulating optional domain, memory, and infrastructure dependencies."""

    db: Optional[DatabaseManager] = None
    memory: Optional[CompanionMemory] = None
    rag: Optional[KnowledgeRAG] = None
    reconciler: Optional[KnowledgeReconciler] = None
    blackboard: Optional[BlackboardPort] = None
    fsm: Optional[Any] = None
    archetype_mgr: Optional[ArchetypeManager] = None
    scaffolder: Optional[ArchetypeScaffolder] = None
    metatuning: Optional[MetaTuningEngine] = None
    history_mgr: Optional[ConversationHistoryManager] = None
    report_coordinator: Optional[TacticalReportToolCoordinator] = None
    factual_resolver: Optional[ContextFactualResolver] = None
    prompt_pipeline: Optional[SystemPromptEnricherPipeline] = None
    context_switch_use_case: Optional[GameContextSwitchUseCase] = None


class AdvisorOrchestrator:
    """Unified generic orchestrator coordinating tactical interaction resolution."""

    def __init__(
        self, config: Optional[AppConfig] = None, provider: Optional[LLMProvider] = None,
        services: Optional[AdvisorServices] = None, report_opener: Optional[Callable[[str], Any]] = None,
        **kwargs: Any,
    ) -> None:
        from abi_coach.application.orchestration.fsm import TacticalFSM

        self.config, self.report_opener = config or AppConfig(), report_opener
        self.provider = provider or create_llm_provider(self.config)
        svc = services or AdvisorServices()
        for k, v in kwargs.items():
            if hasattr(svc, k) and getattr(svc, k) is None:
                setattr(svc, k, v)

        self.blackboard, self.fsm = svc.blackboard or InMemoryBlackboard(), svc.fsm or TacticalFSM()
        self.db = svc.db or getattr(svc.memory, "db", None) or getattr(svc.rag, "db", None) or getattr(svc.reconciler, "db", None) or DatabaseManager()
        self.archetype_mgr = svc.archetype_mgr or ArchetypeManager(self.db)
        self.scaffolder = svc.scaffolder or ArchetypeScaffolder(self.db, self.archetype_mgr)
        self.active_context_id = getattr(self.config.gemini, "game", "generic") or "generic"
        self.memory = svc.memory or CompanionMemory(self.db, default_game=self.active_context_id)
        self.rag = svc.rag or KnowledgeRAG(self.db, default_game=self.active_context_id)
        self.reconciler = svc.reconciler or KnowledgeReconciler(self.db, self.rag)

        if not self.archetype_mgr.get_context(self.active_context_id):
            dname = "Arena Breakout: Infinite" if self.active_context_id in ("abi", "arena_breakout", "arena_breakout_infinite") else ("Game Advisor Universal" if self.active_context_id == "generic" else None)
            self.scaffolder.bootstrap_context(context_id=self.active_context_id, display_name=dname, activate=True)

        self.metatuning = svc.metatuning or MetaTuningEngine(db=self.db, archetype_mgr=self.archetype_mgr, scaffolder=self.scaffolder, config=self.config, report_opener=self.report_opener)
        self.pipeline = ExecutionPipeline([ExceptionHandlingMiddleware(), LoggingMiddleware()])
        self._prompt_registry = PromptTemplateRegistry()
        self.prompt_pipeline = svc.prompt_pipeline or SystemPromptEnricherPipeline(self._prompt_registry)
        self.history_mgr = svc.history_mgr or ConversationHistoryManager(50)
        self.history: List[Turn] = self.history_mgr._turns

        rep = getattr(self.config, "reports", None)
        self.report_coordinator = svc.report_coordinator or TacticalReportToolCoordinator(
            output_dir=getattr(rep, "output_dir", None), auto_open=getattr(rep, "auto_open_browser", True),
            opener=self.report_opener, preferred_browser=getattr(rep, "preferred_browser", None),
            focus_browser=getattr(rep, "focus_browser", False),
        )
        self.context_switch_use_case = svc.context_switch_use_case or GameContextSwitchUseCase(
            archetype_mgr=self.archetype_mgr, scaffolder=self.scaffolder,
            report_coordinator=self.report_coordinator, history_mgr=self.history_mgr,
            config=self.config, memory=self.memory, rag=self.rag,
        )
        self.factual_resolver = svc.factual_resolver or ContextFactualResolver(rag=self.rag, archetype_mgr=self.archetype_mgr)

    @property
    def client(self) -> Any: return getattr(self.provider, "client", None)

    @property
    def current_game(self) -> str: return self.active_context_id

    @current_game.setter
    def current_game(self, val: str) -> None: self.active_context_id = val

    @property
    def _last_report_path(self) -> Optional[str]: return self.report_coordinator.last_report_path

    @_last_report_path.setter
    def _last_report_path(self, val: Optional[str]) -> None: self.report_coordinator.last_report_path = val

    def switch_context(self, new_context_id: str, new_display_name: Optional[str] = None, archetype_id: Optional[str] = None) -> TopicContext:
        ctx = self.context_switch_use_case.execute(new_context_id, new_display_name, archetype_id)
        self.active_context_id = ctx.context_id
        return ctx

    def detect_context_switch_request(self, prompt: str) -> Optional[tuple[str, str]]:
        return self.context_switch_use_case.detect_request(prompt)

    def get_system_instruction(self) -> str:
        return self.prompt_pipeline.build_system_instruction(
            game_id=self.active_context_id,
            custom_instruction=getattr(getattr(self.config, "gemini", None), "system_instruction", None),
            archetype_mgr=self.archetype_mgr, memory=self.memory,
        )

    def try_fast_path(self, prompt: str) -> Optional[InteractionResult]:
        return self._try_fast_path(prompt, self.active_context_id)

    def execute(self, request: InteractionRequest) -> InteractionResult:
        """Execute interaction request through deterministic lookup or generative LLM pipeline."""
        start_time = time.perf_counter()
        prompt = (request.prompt or "").strip()
        active_context_id = request.context_id or self.active_context_id

        # 1. Voice interception / 2. Context switch / 3. Meta-tuning / 4. Fast-path / 5. LLM
        intercept = self._check_voice_intercept(prompt, start_time)
        if intercept: return intercept

        switch_res = self._check_context_switch(prompt)
        if switch_res:
            self.active_context_id = getattr(self.config.gemini, "game", self.active_context_id)
            return switch_res

        tuning_res = self._check_metatuning(prompt, active_context_id, start_time)
        if tuning_res: return tuning_res

        if not request.image_bytes and not request.crop_bytes:
            fast_res = self._try_fast_path(prompt, active_context_id)
            if fast_res: return fast_res

        res = self._invoke_generative_llm(request, active_context_id, start_time)
        self.active_context_id = getattr(self.config.gemini, "game", self.active_context_id)
        return res

    def ask(self, prompt: str, image_bytes: Optional[bytes] = None, crop_bytes: Optional[Dict[str, bytes]] = None, screenshot: Optional[bytes] = None, **kwargs: Any) -> InteractionResult:
        return self.execute(InteractionRequest(prompt=prompt, image_bytes=image_bytes or screenshot, crop_bytes=crop_bytes, context_id=self.active_context_id))

    def ask_result(self, prompt: str, image_bytes: Optional[bytes] = None, crop_bytes: Optional[Dict[str, bytes]] = None, screenshot: Optional[bytes] = None, **kwargs: Any) -> Result[InteractionResult, DomainError]:
        @dataclass(frozen=True)
        class _Cmd:
            prompt: str
            img: Optional[bytes]
            crop: Optional[Dict[str, bytes]]
        def _h(cmd: _Cmd) -> Result[InteractionResult, DomainError]:
            try: return ok(self.ask(prompt=cmd.prompt, image_bytes=cmd.img, crop_bytes=cmd.crop))
            except Exception as exc:
                err = getattr(exc, "_domain_error", None)
                if isinstance(err, DomainError): return fail(err)
                raise
        return self.pipeline.execute(_Cmd(prompt, image_bytes or screenshot, crop_bytes), _h)

    def _check_voice_intercept(self, prompt: str, start_time: float) -> Optional[InteractionResult]:
        if not (self.fsm and hasattr(self.fsm, "intercept_voice_command")): return None
        silence_reply = self.fsm.intercept_voice_command(prompt)
        if not silence_reply: return None
        if self.blackboard and hasattr(self.blackboard, "set_tactical_state"):
            self.blackboard.set_tactical_state(self.fsm.state)
        self.history_mgr.add_user_coach(prompt, silence_reply)
        return InteractionResult(spoken_text=silence_reply, report_path=self.report_coordinator.last_report_path, latency_ms=(time.perf_counter() - start_time) * 1000)

    def _check_context_switch(self, prompt: str) -> Optional[InteractionResult]:
        return self.context_switch_use_case.handle_verbal_switch(prompt) if self.context_switch_use_case else None

    def _check_metatuning(self, prompt: str, context_id: str, start_time: float) -> Optional[InteractionResult]:
        if not (self.metatuning and hasattr(self.metatuning, "process")): return None
        tuning = self.metatuning.process(prompt, context_id)
        if not tuning: return None
        self.history_mgr.add_user_coach(prompt, tuning.spoken_response)
        return InteractionResult(spoken_text=tuning.spoken_response, report_path=tuning.report_path or self.report_coordinator.last_report_path, latency_ms=(time.perf_counter() - start_time) * 1000)

    def _try_fast_path(self, prompt: str, context_id: str) -> Optional[InteractionResult]:
        if not self.factual_resolver: return None
        spoken = self.factual_resolver.try_resolve_factual(prompt, context_id)
        if not spoken: return None
        self.history_mgr.add_user_coach(prompt, spoken)
        return InteractionResult(spoken_text=spoken, latency_ms=1.5)

    def _assemble_history_context(self, prompt: str, context_id: str) -> List[str]:
        max_turns = max(0, getattr(getattr(self.config, "history", None), "max_turns", 5)) if self.config else 5
        lines = self.history_mgr.get_history_slice(max_turns)
        if self.rag and hasattr(self.rag, "format_context_for_prompt"):
            rag_ctx = self.rag.format_context_for_prompt(prompt, game=context_id, limit=2)
            if rag_ctx: lines.append(rag_ctx)
        if self.archetype_mgr and hasattr(self.archetype_mgr, "format_rag_for_prompt"):
            v2_ctx = self.archetype_mgr.format_rag_for_prompt(prompt, context_id=context_id, limit=2)
            if v2_ctx: lines.append(v2_ctx)
        if self.blackboard and hasattr(self.blackboard, "get_state"):
            bb = self.blackboard.get_state()
            if getattr(bb, "screen_summary", None): lines.append(f"[ESTADO VISUAL EN MEMORIA]: {bb.screen_summary}")
            if getattr(bb, "state", None) and bb.state != TacticalState.EXPLORING: lines.append(f"[ESTADO TÁCTICO ACTUAL]: {bb.state.value.upper()}")
        return lines

    def _invoke_generative_llm(self, request: InteractionRequest, context_id: str, start_time: float) -> InteractionResult:
        history_lines = self._assemble_history_context(request.prompt, context_id)
        custom_p = getattr(getattr(self.config, "gemini", None), "system_instruction", None) if self.config else None
        sys_inst = self.prompt_pipeline.build_system_instruction(game_id=context_id, custom_instruction=custom_p, archetype_mgr=self.archetype_mgr, memory=self.memory)

        tool_cb = self.report_coordinator.create_tool_callback()
        raw = self.provider.generate(
            prompt=request.prompt, system_instruction=sys_inst, image_bytes=request.image_bytes,
            crop_bytes=request.crop_bytes, history_text=history_lines, tool_callback=tool_cb,
        )

        if isinstance(raw, Failure):
            err = raw.error
            exc = RuntimeError(getattr(err, "message", str(err)))
            exc._domain_error = err  # type: ignore[attr-defined]
            raise exc
        elif isinstance(raw, Success):
            dto = raw.unwrap()
            spoken, in_tok, out_tok = dto.spoken_text or "", dto.tokens.input_tokens, dto.tokens.output_tokens
            rep_path, lat, p_name = self.report_coordinator.last_report_path, dto.latency_ms, getattr(dto, "provider_name", "gemini")
        else:
            spoken = getattr(raw, "spoken_text", "") or ""
            in_tok, out_tok = getattr(raw, "input_tokens", 0), getattr(raw, "output_tokens", 0)
            rep_path = getattr(raw, "report_path", None) or self.report_coordinator.last_report_path
            lat, p_name = getattr(raw, "latency_ms", 0.0), getattr(raw, "provider_name", "gemini")

        self.history_mgr.add_user_coach(request.prompt, spoken)
        final_lat = lat if lat > 0 else (time.perf_counter() - start_time) * 1000
        return InteractionResult(spoken_text=spoken, report_path=rep_path, input_tokens=in_tok, output_tokens=out_tok, latency_ms=final_lat, provider_name=p_name)
