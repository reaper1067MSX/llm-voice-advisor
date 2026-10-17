"""Tactical advice multimodal orchestration use case."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.application.services.prompt_registry import PromptTemplateRegistry
from abi_coach.application.services.report_coordinator import TacticalReportToolCoordinator
from abi_coach.application.use_cases import CoachResponse
from abi_coach.application.use_cases.context_switch import GameContextSwitchUseCase
from abi_coach.application.use_cases.fast_path_query import FastPathQueryUseCase
from abi_coach.domain.common.result import Failure, Success
from abi_coach.domain.entities.tactical_state import TacticalState


class TacticalAdviceUseCase:
    """Orchestrates multimodal context assembly, RAG, memory profile, and LLM inference."""

    def __init__(
        self,
        provider: Any,
        prompt_registry: PromptTemplateRegistry,
        history_mgr: ConversationHistoryManager,
        report_coordinator: TacticalReportToolCoordinator,
        fast_path_use_case: Optional[FastPathQueryUseCase] = None,
        context_switch_use_case: Optional[GameContextSwitchUseCase] = None,
        metatuning: Optional[Any] = None,
        fsm: Optional[Any] = None,
        blackboard: Optional[Any] = None,
        rag: Optional[Any] = None,
        archetype_mgr: Optional[Any] = None,
        memory: Optional[Any] = None,
        config: Optional[Any] = None,
    ) -> None:
        self.provider = provider
        self.prompt_registry = prompt_registry
        self.history_mgr = history_mgr
        self.report_coordinator = report_coordinator
        self.fast_path_use_case = fast_path_use_case
        self.context_switch_use_case = context_switch_use_case
        self.metatuning = metatuning
        self.fsm = fsm
        self.blackboard = blackboard
        self.rag = rag
        self.archetype_mgr = archetype_mgr
        self.memory = memory
        self.config = config

    def execute(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        crop_bytes: Optional[Dict[str, bytes]] = None,
        active_context_id: str = "generic",
    ) -> CoachResponse:
        """Execute multimodal tactical reasoning through context pipelines."""
        start_time = time.perf_counter()

        # 0. Intercept voice silence / focus mode commands instantly
        if self.fsm and hasattr(self.fsm, "intercept_voice_command"):
            silence_reply = self.fsm.intercept_voice_command(prompt)
            if silence_reply:
                if self.blackboard and hasattr(self.blackboard, "set_tactical_state"):
                    self.blackboard.set_tactical_state(self.fsm.state)
                self.history_mgr.add_user_coach(prompt, silence_reply)
                return CoachResponse(
                    spoken_text=silence_reply,
                    report_path=self.report_coordinator.last_report_path,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=(time.perf_counter() - start_time) * 1000,
                )

        # 1. Check verbal context switch
        if self.context_switch_use_case:
            switch_res = self.context_switch_use_case.handle_verbal_switch(prompt)
            if switch_res:
                return switch_res

        # 2. Check meta-tuning configuration commands
        if self.metatuning and hasattr(self.metatuning, "process"):
            tuning_res = self.metatuning.process(prompt, active_context_id)
            if tuning_res:
                self.history_mgr.add_user_coach(prompt, tuning_res.spoken_response)
                return CoachResponse(
                    spoken_text=tuning_res.spoken_response,
                    report_path=tuning_res.report_path or self.report_coordinator.last_report_path,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=(time.perf_counter() - start_time) * 1000,
                )

        # 3. Fast-Path local retrieval check
        if not image_bytes and not crop_bytes and self.fast_path_use_case:
            fast_reply = self.fast_path_use_case.execute(prompt, active_context_id)
            if fast_reply:
                return fast_reply

        # 4. Multimodal context assembly
        max_turns = max(0, getattr(getattr(self.config, "history", None), "max_turns", 5)) if self.config else 5
        history_lines = self.history_mgr.get_history_slice(max_turns)

        game_name = active_context_id or "generic"
        if self.rag and hasattr(self.rag, "format_context_for_prompt"):
            rag_ctx = self.rag.format_context_for_prompt(prompt, game=game_name, limit=2)
            if rag_ctx:
                history_lines.append(rag_ctx)
        if self.archetype_mgr and hasattr(self.archetype_mgr, "format_rag_for_prompt"):
            v2_ctx = self.archetype_mgr.format_rag_for_prompt(prompt, context_id=game_name, limit=2)
            if v2_ctx:
                history_lines.append(v2_ctx)

        if self.blackboard and hasattr(self.blackboard, "get_state"):
            bb = self.blackboard.get_state()
            if getattr(bb, "screen_summary", None):
                history_lines.append(f"[ESTADO VISUAL EN MEMORIA]: {bb.screen_summary}")
            if getattr(bb, "state", None) and bb.state != TacticalState.EXPLORING:
                history_lines.append(f"[ESTADO TÁCTICO ACTUAL]: {bb.state.value.upper()}")

        custom_prompt = getattr(getattr(self.config, "gemini", None), "system_instruction", None) if self.config else None
        sys_inst = self.prompt_registry.build_system_instruction(
            game_id=game_name,
            custom_instruction=custom_prompt,
            archetype_mgr=self.archetype_mgr,
            memory=self.memory,
        )

        tool_cb = self.report_coordinator.create_tool_callback()
        raw_res = self.provider.generate(
            prompt=prompt,
            system_instruction=sys_inst,
            image_bytes=image_bytes,
            crop_bytes=crop_bytes,
            history_text=history_lines,
            tool_callback=tool_cb,
        )

        if isinstance(raw_res, Failure):
            err = raw_res.error
            exc = RuntimeError(getattr(err, "message", str(err)))
            exc._domain_error = err  # type: ignore[attr-defined]
            raise exc
        elif isinstance(raw_res, Success):
            dto = raw_res.unwrap()
            spoken = dto.spoken_text or ""
            in_tok, out_tok = dto.tokens.input_tokens, dto.tokens.output_tokens
            rep_path = self.report_coordinator.last_report_path
            res_lat = dto.latency_ms
            p_name = getattr(dto, "provider_name", "gemini")
        else:
            spoken = getattr(raw_res, "spoken_text", "") or ""
            in_tok = getattr(raw_res, "input_tokens", 0)
            out_tok = getattr(raw_res, "output_tokens", 0)
            rep_path = getattr(raw_res, "report_path", None) or self.report_coordinator.last_report_path
            res_lat = getattr(raw_res, "latency_ms", 0.0)
            p_name = getattr(raw_res, "provider_name", "gemini")

        self.history_mgr.add_user_coach(prompt, spoken)
        latency = res_lat if res_lat > 0 else (time.perf_counter() - start_time) * 1000

        return CoachResponse(
            spoken_text=spoken,
            report_path=rep_path,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency,
            provider_name=p_name,
        )
