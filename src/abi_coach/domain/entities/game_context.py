"""Game Context Aggregate Root (Domain Layer)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from abi_coach.domain.common.value_objects import TopicKey


@dataclass
class GameContext:
    """Aggregate Root representing an active or configured gaming context."""

    context_id: str
    archetype_id: str = "general_companion"
    display_name: str = "Universal Game Advisor"
    version: str = "1.0.0"
    is_active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    rules: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.context_id = self.context_id.strip().lower()
        if not self.context_id:
            raise ValueError("context_id cannot be empty.")

    def activate(self) -> None:
        """Set context as actively tracked by the copilot."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate context."""
        self.is_active = False

    def add_rule(self, rule_text: str) -> None:
        """Add an active tactical rule to this context."""
        r = rule_text.strip()
        if r and r not in self.rules:
            self.rules.append(r)
