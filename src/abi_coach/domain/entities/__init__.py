"""Domain Entities and Aggregates package."""

from abi_coach.domain.entities.context_switch_records import ContextSwitchRequest
from abi_coach.domain.entities.dashboard_records import KnowledgeDashboardItem, MemoryDashboardItem
from abi_coach.domain.entities.game_context import GameContext
from abi_coach.domain.entities.interaction_records import CoachResponse, InteractionRequest, InteractionResult
from abi_coach.domain.entities.metatuning_records import (
    CANCELLATION_PHRASES,
    CONFIRMATION_RULES,
    ClarificationResolution,
    ClarificationState,
    ParsedConfig,
    ParsedFact,
    ParsedRule,
    RESOLUTION_RULES,
    RuleMapping,
    VOICE_MAP,
    is_cancellation_phrase,
)
from abi_coach.domain.entities.player_memory import PlayerMemory
from abi_coach.domain.entities.tactical_fact import TacticalDiff, TacticalFact
from abi_coach.domain.entities.tactical_state import GameStateContext, TacticalState
from abi_coach.domain.entities.tuning_rule import MetaTuningDirective, TuningRule

__all__ = [
    "GameContext",
    "PlayerMemory",
    "TacticalFact",
    "TacticalDiff",
    "TuningRule",
    "MetaTuningDirective",
    "TacticalState",
    "GameStateContext",
    "InteractionRequest",
    "InteractionResult",
    "CoachResponse",
    "ContextSwitchRequest",
    "RuleMapping",
    "ParsedConfig",
    "ParsedRule",
    "ParsedFact",
    "ClarificationResolution",
    "ClarificationState",
    "CANCELLATION_PHRASES",
    "VOICE_MAP",
    "RESOLUTION_RULES",
    "CONFIRMATION_RULES",
    "is_cancellation_phrase",
    "MemoryDashboardItem",
    "KnowledgeDashboardItem",
]
