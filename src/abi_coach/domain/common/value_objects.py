"""Domain Value Objects encapsulating validation invariants and immutability."""

from dataclasses import dataclass
import re
from typing import Optional


@dataclass(frozen=True)
class TopicKey:
    """Hierarchical, immutable topic identifier (game/topic/facet)."""

    value: str

    def __post_init__(self):
        v = (self.value or "").strip().lower()
        if not v:
            raise ValueError("TopicKey cannot be empty.")
        # Ensure it contains alphanumeric, slashes, hyphens, or underscores
        if not re.match(r"^[a-z0-9_\-\/]+$", v):
            raise ValueError(f"Invalid characters in TopicKey: '{v}'")
        object.__setattr__(self, "value", v)

    @classmethod
    def create(cls, game: str, topic: str, facet: str) -> "TopicKey":
        """Factory method building standard game/topic/facet key."""
        g = re.sub(r"[^a-z0-9_]+", "_", game.strip().lower()).strip("_") or "generic"
        t = re.sub(r"[^a-z0-9_]+", "_", topic.strip().lower()).strip("_") or "general"
        f = re.sub(r"[^a-z0-9_]+", "_", facet.strip().lower()).strip("_") or "main"
        return cls(f"{g}/{t}/{f}")

    @property
    def game(self) -> str:
        parts = self.value.split("/")
        return parts[0] if len(parts) > 0 else "generic"

    @property
    def topic(self) -> str:
        parts = self.value.split("/")
        return parts[1] if len(parts) > 1 else "general"

    @property
    def facet(self) -> str:
        parts = self.value.split("/")
        return parts[2] if len(parts) > 2 else "main"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ArmorTier:
    """Ballistic protection or loot quality tier (1 to 6)."""

    tier: int

    def __post_init__(self):
        if not (1 <= self.tier <= 6):
            raise ValueError(f"ArmorTier must be between 1 and 6, got {self.tier}")

    @property
    def color_class(self) -> str:
        colors = {
            1: "tier1",  # gray
            2: "tier2",  # green
            3: "tier3",  # blue
            4: "tier4",  # purple
            5: "tier5",  # pink
            6: "tier6",  # gold
        }
        return colors.get(self.tier, "tier1")

    @property
    def label(self) -> str:
        return f"Tier {self.tier}"


@dataclass(frozen=True)
class ConfidenceScore:
    """Statistical confidence bounded in [0.0, 1.0]."""

    score: float

    def __post_init__(self):
        val = max(0.0, min(1.0, float(self.score)))
        object.__setattr__(self, "score", val)

    def is_reliable(self, threshold: float = 0.8) -> bool:
        return self.score >= threshold


@dataclass(frozen=True)
class TokenUsage:
    """Tracks token consumption for auditing and rate limiting."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
