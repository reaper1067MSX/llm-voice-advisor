"""Generic Advisor Process Orchestrator unifiying deterministic fast path and multimodal LLM."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from abi_coach.application.services.context_factual_resolver import ContextFactualResolver
from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.application.services.prompt_enricher import SystemPromptEnricherPipeline
from abi_coach.application.services.report_coordinator import TacticalReportToolCoordinator
from abi_coach.application.use_cases.context_switch import GameContextSwitchUseCase
from abi_coach.domain.common.result import Failure, Success
from abi_coach.domain.entities.interaction_records import InteractionRequest, InteractionResult
from abi_coach.domain.entities.tactical_state import TacticalState
from abi_coach.domain.ports.history_port import ConversationHistoryPort


class AdvisorOrchestrator:
    """Unified generic orchestrator coordinating tactical interaction resolution."""

    def __init__(
        self,
        provider: Any,
        prompt_pipeline: Optional[SystemPromptEnricherPipeline] = None,
        history_mgr: Optional[ConversationHistoryPort] = None,
        report_coordinator: Optional[TacticalReportToolCoordinator] = None,
        factual_resolver: Optional[ContextFactualResolver] = None,
        context_switch_use_case: Optional[GameContextSwitchUseCase] = None,
        fsm: Optional[Any] = None,
        blackboard: Optional[Any] = None,
        metatuning: Optional[Any] = None,
        rag: Optional[Any] = None,
        archetype_mgr: Optional[Any] = None,
        memory: Optional[Any] = None,
        config: Optional[Any] = None,
    ) -> None:
        self.provider = provider
        self.prompt_pipeline = prompt_pipeline or SystemPromptEnricherPipeline()
        self.history_mgr = history_mgr or ConversationHistoryManager(50)
        self.report_coordinator = report_coordinator or TacticalReportToolCoordinator(auto_open=False)
        self.factual_resolver = factual_resolver or ContextFactualResolver(rag=rag, archetype_mgr=archetype_mgr)
        self.context_switch_use_case = context_switch_use_case
        self.fsm = fsm
        self.blackboard = blackboard
        self.metatuning = metatuning
        self.rag = rag
        self.archetype_mgr = archetype_mgr
        self.memory = memory
        self.config = config

    def execute(self, request: InteractionRequest) -> InteractionResult:
        """Execute interaction request through deterministic lookup or generative LLM pipeline."""
        start_time = time.perf_counter()
        prompt = (request.prompt or "").strip()
        active_context_id = request.context_id or getattr(getattr(self.config, "gemini", None), "game", "generic") or "generic"

        # 1. Voice interception (FSM silence / radio discipline)
        intercept = self._check_voice_intercept(prompt, start_time)
        if intercept:
            return intercept

        # 2. Verbal context switch
        switch_res = self._check_context_switch(prompt)
        if switch_res:
            return switch_res

        # 3. Meta-tuning directives
        tuning_res = self._check_metatuning(prompt, active_context_id, start_time)
        if tuning_res:
            return tuning_res

        # 4. Deterministic fast-path factual resolution (sub-2ms)
        if not request.image_bytes and not request.crop_bytes:
            fast_res = self._try_fast_path(prompt, active_context_id)
            if fast_res:
                return fast_res

        # 5. Generative Multimodal LLM fallback
        return self._invoke_generative_llm(request, active_context_id, start_time)

    def _check_voice_intercept(self, prompt: str, start_time: float) -> Optional[InteractionResult]:
        if not (self.fsm and hasattr(self.fsm, "intercept_voice_command")):
            return None
        silence_reply = self.fsm.intercept_voice_command(prompt)
        if not silence_reply:
            return None
        if self.blackboard and hasattr(self.blackboard, "set_tactical_state"):
            self.blackboard.set_tactical_state(self.fsm.state)
        self.history_mgr.add_user_coach(prompt, silence_reply)
        return InteractionResult(
            spoken_text=silence_reply,
            report_path=self.report_coordinator.last_report_path,
            latency_ms=(time.perf_counter() - start_time) * 1000,
        )

    def _check_context_switch(self, prompt: str) -> Optional[InteractionResult]:
        if not self.context_switch_use_case:
            return None
        return self.context_switch_use_case.handle_verbal_switch(prompt)

    def _check_metatuning(self, prompt: str, context_id: str, start_time: float) -> Optional[InteractionResult]:
        if not (self.metatuning and hasattr(self.metatuning, "process")):
            return None
        tuning = self.metatuning.process(prompt, context_id)
        if not tuning:
            return None
        self.history_mgr.add_user_coach(prompt, tuning.spoken_response)
        return InteractionResult(
            spoken_text=tuning.spoken_response,
            report_path=tuning.report_path or self.report_coordinator.last_report_path,
            latency_ms=(time.perf_counter() - start_time) * 1000,
        )

    def _try_fast_path(self, prompt: str, context_id: str) -> Optional[InteractionResult]:
        if not self.factual_resolver:
            return None
        spoken = self.factual_resolver.try_resolve_factual(prompt, context_id)
        if not spoken:
            return None
        self.history_mgr.add_user_coach(prompt, spoken)
        return InteractionResult(spoken_text=spoken, latency_ms=1.5)

    def _assemble_history_context(self, prompt: str, context_id: str) -> List[str]:
        max_turns = max(0, getattr(getattr(self.config, "history", None), "max_turns", 5)) if self.config else 5
        lines = self.history_mgr.get_history_slice(max_turns)
        if self.rag and hasattr(self.rag, "format_context_for_prompt"):
            rag_ctx = self.rag.format_context_for_prompt(prompt, game=context_id, limit=2)
            if rag_ctx:
                lines.append(rag_ctx)
        if self.archetype_mgr and hasattr(self.archetype_mgr, "format_rag_for_prompt"):
            v2_ctx = self.archetype_mgr.format_rag_for_prompt(prompt, context_id=context_id, limit=2)
            if v2_ctx:
                lines.append(v2_ctx)
        if self.blackboard and hasattr(self.blackboard, "get_state"):
            bb = self.blackboard.get_state()
            if getattr(bb, "screen_summary", None):
                lines.append(f"[ESTADO VISUAL EN MEMORIA]: {bb.screen_summary}")
            if getattr(bb, "state", None) and bb.state != TacticalState.EXPLORING:
                lines.append(f"[ESTADO TÁCTICO ACTUAL]: {bb.state.value.upper()}")
        return lines

    def _invoke_generative_llm(
        self, request: InteractionRequest, context_id: str, start_time: float
    ) -> InteractionResult:
        history_lines = self._assemble_history_context(request.prompt, context_id)
        custom_p = getattr(getattr(self.config, "gemini", None), "system_instruction", None) if self.config else None
        sys_inst = self.prompt_pipeline.build_system_instruction(
            game_id=context_id,
            custom_instruction=custom_p,
            archetype_mgr=self.archetype_mgr,
            memory=self.memory,
        )

        tool_cb = self.report_coordinator.create_tool_callback()
        raw = self.provider.generate(
            prompt=request.prompt,
            system_instruction=sys_inst,
            image_bytes=request.image_bytes,
            crop_bytes=request.crop_bytes,
            history_text=history_lines,
            tool_callback=tool_cb,
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
        return InteractionResult(
            spoken_text=spoken,
            report_path=rep_path,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=final_lat,
            provider_name=p_name,
        )
