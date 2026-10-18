"""Domain records alias for tactical query and interaction requests."""

from abi_coach.domain.entities.interaction_records import (
    CoachResponse,
    InteractionRequest,
    InteractionResult,
)

TacticalQuery = InteractionRequest
TacticalQueryResult = InteractionResult

__all__ = [
    "CoachResponse",
    "InteractionRequest",
    "InteractionResult",
    "TacticalQuery",
    "TacticalQueryResult",
]
