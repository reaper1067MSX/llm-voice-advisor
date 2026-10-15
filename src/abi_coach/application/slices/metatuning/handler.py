"""Meta-Tuning Vertical Slice (Application Layer)."""

from dataclasses import dataclass
from typing import Optional

from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result, ok
from abi_coach.domain.entities.tuning_rule import MetaTuningDirective
from abi_coach.slices.metatuning.engine import MetaTuningEngine


@dataclass(frozen=True)
class ProcessMetaTuningCommand:
    prompt: str
    context_id: str = "generic"


class MetaTuningHandler:
    """Use Case Handler for conversational meta-tuning with clarification loop."""

    def __init__(self, engine: MetaTuningEngine):
        self.engine = engine

    def handle(self, command: ProcessMetaTuningCommand) -> Result[Optional[MetaTuningDirective], DomainError]:
        res = self.engine.process(command.prompt, command.context_id)
        if res is None:
            return ok(None)

        directive = MetaTuningDirective(
            intent=res.target_type or "rule",
            action_taken=res.action_taken,
            spoken_feedback=res.spoken_response,
            is_clarification_needed=res.is_clarification,
            details=res.details,
        )
        return ok(directive)
