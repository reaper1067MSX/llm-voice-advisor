"""Tactical Fact and Reconciliation Entities (Domain Layer)."""

from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, Optional
from abi_coach.domain.common.value_objects import ConfidenceScore


@dataclass
class TacticalFact:
    """Represents a factual tactical item, weapon statistic, or game mechanic."""

    game: str
    category: str
    entity_key: str
    title: str
    data_payload: Dict[str, Any]
    summary: str
    source: str = "official_patch"
    confidence: ConfidenceScore = field(default_factory=lambda: ConfidenceScore(1.0))
    game_version: str = "1.0"
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self):
        now = time.time()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        self.game = self.game.strip().lower()
        self.entity_key = self.entity_key.strip().lower()


@dataclass(frozen=True)
class TacticalDiff:
    """Discrepancy detected between stored fact and live visual observation."""

    entity_key: str
    field_name: str
    old_value: Any
    new_value: Any
    reason: str
    confidence: float = 0.95
