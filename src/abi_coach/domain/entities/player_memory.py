"""Player Memory Entity (Domain Layer)."""

from dataclasses import dataclass
import time
from typing import Optional
from abi_coach.domain.common.value_objects import TopicKey


@dataclass
class PlayerMemory:
    """Represents a discrete persistent player preference or tactical observation."""

    topic_key: TopicKey
    title: str
    content: str
    memory_type: str = "preference"  # preference, discovery, decision, rule
    pinned: bool = False
    access_count: int = 0
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self):
        now = time.time()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def mark_accessed(self) -> None:
        """Increment usage metric and update timestamp."""
        self.access_count += 1
        self.updated_at = time.time()

    def pin(self) -> None:
        """Pin memory to ensure high prompt priority."""
        self.pinned = True
        self.updated_at = time.time()

    def unpin(self) -> None:
        """Unpin memory."""
        self.pinned = False
        self.updated_at = time.time()
