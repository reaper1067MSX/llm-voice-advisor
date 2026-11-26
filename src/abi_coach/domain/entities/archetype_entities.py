"""Domain entities and constants for dynamic archetypes, contexts, and Engram observations."""

from dataclasses import dataclass, field
from typing import Any

SPANISH_FTS_STOPWORDS: tuple[str, ...] = (
    "de",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "en",
    "con",
    "por",
    "para",
    "que",
    "qué",
)


@dataclass
class ArchetypeDefinition:
    """Foundational domain archetype blueprint for a family of games or topics."""

    archetype_id: str
    display_name: str
    schema_template: dict[str, Any]
    default_system_prompt: str


@dataclass
class TopicContext:
    """An instantiated topic domain / game context linked to an archetype."""

    context_id: str
    archetype_id: str
    display_name: str
    current_version: str = "1.0"
    config: dict[str, Any] = field(default_factory=dict)
    is_active: bool = False


@dataclass
class DynamicEntity:
    """Entity with dynamic facet attributes (no rigid ballistic columns)."""

    context_id: str
    category: str
    entity_key: str
    title: str
    facets: dict[str, Any]
    summary: str
    confidence: float = 1.0
    source: str = "system"


@dataclass
class EngramObservation:
    """Engram-compliant observation representing learned player patterns and rules."""

    context_id: str
    scope: str
    topic_key: str
    observation_type: str
    title: str
    content: str
    pinned: bool = False
    access_count: int = 0


__all__ = [
    "SPANISH_FTS_STOPWORDS",
    "ArchetypeDefinition",
    "TopicContext",
    "DynamicEntity",
    "EngramObservation",
]
