"""Domain Entities and Immutable Records for Meta-Tuning."""

from dataclasses import dataclass, field
import re
import time
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class RuleMapping:
    """Predefined tactical rule mapping with trigger keywords and resolution content."""

    keywords: Tuple[str, ...]
    title: str
    slug: str
    what: str
    learned: str

    def __iter__(self):
        """Allow seamless unpacking as a 5-tuple for backward compatibility."""
        return iter((self.keywords, self.title, self.slug, self.what, self.learned))

    def __getitem__(self, index: int) -> Any:
        return (self.keywords, self.title, self.slug, self.what, self.learned)[index]

    def __len__(self) -> int:
        return 5


@dataclass(frozen=True)
class ParsedConfig:
    """Parsed configuration modification target."""

    key_path: List[str]
    value: Any
    message: str
    key_name: str


@dataclass(frozen=True)
class ParsedRule:
    """Parsed direct behavioral rule."""

    title: str
    slug: str
    what: str
    learned: str


@dataclass(frozen=True)
class ParsedFact:
    """Parsed factual knowledge for RAG ingestion."""

    title: str
    category: str
    summary: str


@dataclass(frozen=True)
class ClarificationResolution:
    """Resolved clarification outcome mapped to a persistent rule."""

    title: str
    slug: str
    what: str
    learned: str


@dataclass
class ClarificationState:
    """State of a pending clarification dialogue with TTL support."""

    original_prompt: str
    context_id: str = "generic"
    category: str = "general"
    created_at: float = field(default_factory=time.time)

    @property
    def timestamp(self) -> float:
        return self.created_at

    def get(self, key: str, default: Any = None) -> Any:
        if key == "timestamp":
            return self.created_at
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        if key == "timestamp":
            return self.created_at
        return getattr(self, key)


CANCELLATION_PHRASES: Tuple[str, ...] = (
    "cancela",
    "cancelar",
    "olvídalo",
    "olvidalo",
    "no importa",
)

VOICE_MAP: Dict[str, str] = {
    "salome": "es-CO-SalomeNeural",
    "salomé": "es-CO-SalomeNeural",
    "elvira": "es-ES-ElviraNeural",
    "ximena": "es-ES-XimenaNeural",
    "camila": "es-PE-CamilaNeural",
    "paloma": "es-US-PalomaNeural",
    "dalia": "es-MX-DaliaNeural",
    "elena": "es-AR-ElenaNeural",
    "catalina": "es-CL-CatalinaNeural",
}

RESOLUTION_RULES: Tuple[RuleMapping, ...] = (
    RuleMapping(
        keywords=("casilla", "valor"),
        title="Prioridad de Loot por Casilla",
        slug="loot_value_per_slot",
        what="Priorizar estrictamente objetos con mayor valor económico estimado por casilla de inventario.",
        learned="Descartar objetos voluminosos de bajo valor unitario para maximizar rentabilidad.",
    ),
    RuleMapping(
        keywords=("morado", "dorado", "tier"),
        title="Filtro de Objetos de Alto Tier",
        slug="high_tier_loot_only",
        what="Filtrar y alertar únicamente sobre objetos morados, dorados o de Tier 4 o superior.",
        learned="Ignorar loot común o gris para acelerar el ritmo de juego.",
    ),
    RuleMapping(
        keywords=("contrato", "craft", "mision"),
        title="Objetos de Contratos y Crafteo",
        slug="quest_craft_items",
        what="Destacar objetos requeridos para contratos de comerciantes o materiales raros de crafteo.",
        learned="Notificar inmediatamente cuando un objeto coincida con contratos activos.",
    ),
    RuleMapping(
        keywords=("penetracion", "penetración", "blindaje"),
        title="Prioridad Balística: Penetración Máxima",
        slug="max_penetration",
        what="Recomendar exclusivamente munición con penetración capaz de perforar blindajes pesados.",
        learned="Evitar munición de daño a extremidades cuando el objetivo porte armadura Tier 5 o 6.",
    ),
    RuleMapping(
        keywords=("retroceso", "build"),
        title="Builds de Bajo Retroceso",
        slug="low_recoil_builds",
        what="Priorizar estabilidad y reducción de retroceso vertical y horizontal en modificaciones de armas.",
        learned="Favorecer empuñaduras y bocachas de compensación sobre ergonomía pura.",
    ),
)

CONFIRMATION_RULES: Tuple[RuleMapping, ...] = RESOLUTION_RULES


def is_cancellation_phrase(text: str) -> bool:
    """Identify if text matches conversational cancellation expressions."""
    clean = text.strip().lower().strip(".?!,¡¿")
    if clean in CANCELLATION_PHRASES or "no importa" in clean:
        return True
    matched_words = set(re.findall(r"[a-záéíóúñ]+", clean))
    return bool(matched_words & {"cancela", "cancelar", "olvídalo", "olvidalo"})


__all__ = [
    "CANCELLATION_PHRASES",
    "CONFIRMATION_RULES",
    "ClarificationResolution",
    "ClarificationState",
    "ParsedConfig",
    "ParsedFact",
    "ParsedRule",
    "RESOLUTION_RULES",
    "RuleMapping",
    "VOICE_MAP",
    "is_cancellation_phrase",
]
