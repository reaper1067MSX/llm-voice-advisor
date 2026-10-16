"""Tactical Advice Handler (Application Layer)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from abi_coach.application.pipeline import (
    ExceptionHandlingMiddleware,
    ExecutionPipeline,
    LoggingMiddleware,
)
from abi_coach.application.slices.tactical_advice.commands import (
    AskTacticalAdviceCommand,
    TacticalAdviceDTO,
)
from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result, ok
from abi_coach.domain.common.value_objects import TokenUsage
from abi_coach.domain.ports.knowledge_port import KnowledgeRepositoryPort
from abi_coach.domain.ports.llm_port import LLMProviderPort
from abi_coach.domain.ports.memory_port import MemoryRepositoryPort
from abi_coach.domain.ports.vision_port import ReportDisplayPort

if TYPE_CHECKING:
    from abi_coach.application.orchestration.brain import Brain


class TacticalAdviceHandler:
    """Use Case Handler for real-time tactical queries."""

    def __init__(
        self,
        brain: Brain,
        llm_port: Optional[LLMProviderPort] = None,
        knowledge_port: Optional[KnowledgeRepositoryPort] = None,
        memory_port: Optional[MemoryRepositoryPort] = None,
        report_port: Optional[ReportDisplayPort] = None,
        pipeline: Optional[ExecutionPipeline] = None,
    ):
        self.brain = brain
        self.llm_port = llm_port
        self.knowledge_port = knowledge_port
        self.memory_port = memory_port
        self.report_port = report_port
        self.pipeline = pipeline or ExecutionPipeline(
            [ExceptionHandlingMiddleware(), LoggingMiddleware()]
        )

    def _handle(self, command: AskTacticalAdviceCommand) -> Result[TacticalAdviceDTO, DomainError]:
        start = time.perf_counter()
        resp = self.brain.ask(
            prompt=command.prompt,
            image_bytes=command.image_bytes,
            crop_bytes=command.crop_bytes,
        )

        in_tok = resp.input_tokens or 0
        out_tok = resp.output_tokens or 0
        dto = TacticalAdviceDTO(
            spoken_advice=resp.spoken_text,
            report_path=resp.report_path,
            tokens=TokenUsage(input_tokens=in_tok, output_tokens=out_tok),
            latency_ms=resp.latency_ms if resp.latency_ms > 0 else (time.perf_counter() - start) * 1000,
        )
        return ok(dto)

    def handle(self, command: AskTacticalAdviceCommand) -> Result[TacticalAdviceDTO, DomainError]:
        return self.pipeline.execute(command, self._handle)

