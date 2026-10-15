"""Context Switching Vertical Slice (Application Layer)."""

from dataclasses import dataclass
from typing import Optional

from abi_coach.domain.common.errors import DomainError
from abi_coach.domain.common.result import Result, ok
from abi_coach.domain.entities.game_context import GameContext
from abi_coach.orchestration.brain import Brain


@dataclass(frozen=True)
class SwitchContextCommand:
    """Command to dynamically switch active gaming context in RAM & DB."""

    context_id: str
    display_name: Optional[str] = None
    archetype_id: Optional[str] = None


class ContextSwitchHandler:
    """Use Case Handler for game context switching and zero-seeder onboarding."""

    def __init__(self, brain: Brain):
        self.brain = brain

    def handle(self, command: SwitchContextCommand) -> Result[GameContext, DomainError]:
        raw_ctx = self.brain.switch_context(
            new_context_id=command.context_id,
            new_display_name=command.display_name,
            archetype_id=command.archetype_id,
        )
        ctx = GameContext(
            context_id=raw_ctx.context_id,
            archetype_id=raw_ctx.archetype_id,
            display_name=raw_ctx.display_name,
            version=raw_ctx.current_version,
            is_active=True,
        )
        return ok(ctx)
