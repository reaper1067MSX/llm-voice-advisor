"""Blackboard Port interface (Domain Layer)."""

from abc import ABC, abstractmethod
from typing import Optional
from abi_coach.domain.entities.tactical_state import GameStateContext, TacticalState


class BlackboardPort(ABC):
    """Outbound port for reading and writing tactical game state (Blackboard Pattern)."""

    @abstractmethod
    def get_state(self) -> GameStateContext:
        """Retrieve current tactical state snapshot in O(1)."""
        pass

    @abstractmethod
    def update_state(
        self,
        game_id: Optional[str] = None,
        state: Optional[TacticalState] = None,
        screen_summary: Optional[str] = None,
        danger_level: Optional[float] = None,
        entities_in_view: Optional[list] = None,
    ) -> GameStateContext:
        """Atomically update state attributes."""
        pass

    @abstractmethod
    def set_tactical_state(self, state: TacticalState) -> None:
        """Atomically update tactical FSM state."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset blackboard to initial clean state."""
        pass
