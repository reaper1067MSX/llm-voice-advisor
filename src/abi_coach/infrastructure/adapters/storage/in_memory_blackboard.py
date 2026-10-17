"""Thread-safe In-Memory Blackboard Adapter implementing BlackboardPort."""

import threading
import time
from typing import Any, Dict, List, Optional

from abi_coach.domain.entities.tactical_state import GameStateContext, TacticalState
from abi_coach.domain.ports.blackboard_port import BlackboardPort


class InMemoryBlackboard(BlackboardPort):
    """In-memory thread-safe implementation of the Blackboard architectural pattern."""

    def __init__(self, initial_state: Optional[GameStateContext] = None):
        self._lock = threading.RLock()
        self._context = initial_state or GameStateContext()

    def get_state(self) -> GameStateContext:
        """Retrieve a thread-safe copy of the current tactical context in O(1)."""
        with self._lock:
            return GameStateContext(
                game_id=self._context.game_id,
                state=self._context.state,
                screen_summary=self._context.screen_summary,
                danger_level=self._context.danger_level,
                entities_in_view=list(self._context.entities_in_view),
                metadata=dict(self._context.metadata),
                last_updated_at=self._context.last_updated_at,
            )

    def update_state(
        self,
        game_id: Optional[str] = None,
        state: Optional[TacticalState] = None,
        screen_summary: Optional[str] = None,
        danger_level: Optional[float] = None,
        entities_in_view: Optional[List[str]] = None,
    ) -> GameStateContext:
        """Atomically update state attributes and refresh last_updated_at."""
        with self._lock:
            if game_id is not None:
                self._context.game_id = game_id
            if state is not None:
                self._context.state = state
            if screen_summary is not None:
                self._context.screen_summary = screen_summary
            if danger_level is not None:
                self._context.danger_level = max(0.0, min(1.0, float(danger_level)))
            if entities_in_view is not None:
                self._context.entities_in_view = list(entities_in_view)
            self._context.last_updated_at = time.time()
            return self.get_state()

    def set_tactical_state(self, state: TacticalState) -> None:
        """Atomically update tactical FSM state."""
        with self._lock:
            self._context.state = state
            self._context.last_updated_at = time.time()

    def reset(self) -> None:
        """Reset blackboard to initial clean state."""
        with self._lock:
            self._context = GameStateContext()
