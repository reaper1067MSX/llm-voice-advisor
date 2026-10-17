"""Tactical State and Blackboard Context Entities (Domain Layer)."""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class TacticalState(str, Enum):
    """Finite State Machine states representing the tactical situation of the player."""

    LOBBY = "lobby"              # Menus, stash, prep phase (relaxed, strategic)
    EXPLORING = "exploring"      # In-game looting, navigating (alert, proactive tips allowed)
    COMBAT = "combat"            # Gunfight, intense action (radio silence / life-saving warnings only)
    RADIO_SILENCE = "silence"    # Player requested complete silence / concentration mode


@dataclass
class GameStateContext:
    """Real-time tactical snapshot shared across modules via Blackboard Pattern."""

    game_id: str = "generic"
    state: TacticalState = TacticalState.EXPLORING
    screen_summary: str = ""
    danger_level: float = 0.0          # 0.0 (safe) to 1.0 (imminent death/combat)
    entities_in_view: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated_at: float = field(default_factory=time.time)

    def is_in_combat(self) -> bool:
        return self.state == TacticalState.COMBAT or self.danger_level >= 0.7

    def is_silent(self) -> bool:
        return self.state == TacticalState.RADIO_SILENCE
