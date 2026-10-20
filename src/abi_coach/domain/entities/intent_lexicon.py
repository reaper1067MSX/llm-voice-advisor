"""Domain intent lexicon and canonical text normalizer (Domain Layer)."""

from dataclasses import dataclass
from typing import FrozenSet, Tuple
import unicodedata

from abi_coach.domain.enums.metatuning_enums import MetaTuningCategory, MetaTuningIntent


class TextNormalizer:
    """Normalizes natural language text to clean canonical form (NFKD, lower, no diacritics)."""

    @staticmethod
    def normalize(text: str) -> str:
        """Strip diacritics and convert text to lowercase canonical form."""
        if not text:
            return ""
        decomposed = unicodedata.normalize("NFKD", text.strip().lower())
        return "".join(c for c in decomposed if not unicodedata.combining(c))

    @staticmethod
    def tokenize(text: str) -> FrozenSet[str]:
        """Convert text into canonical token set for O(1) membership operations."""
        norm = TextNormalizer.normalize(text)
        return frozenset(norm.split())


@dataclass(frozen=True)
class IntentTriggerDefinition:
    """Encapsulates a typed intent and its canonical activation patterns."""

    intent: MetaTuningIntent
    exact_phrases: Tuple[str, ...]
    keyword_sets: Tuple[Tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class CategoryTriggerDefinition:
    """Encapsulates a domain category and its canonical keywords."""

    category: MetaTuningCategory
    keywords: FrozenSet[str]


@dataclass(frozen=True)
class ProviderMapping:
    """Encapsulates an AI provider identifier and its display label."""

    provider_id: str
    label: str


INTENT_TRIGGERS: Tuple[IntentTriggerDefinition, ...] = (
    IntentTriggerDefinition(
        intent=MetaTuningIntent.CONFIG,
        exact_phrases=(
            "configuracion global",
            "ajustes globales",
            "cambiar configuracion",
        ),
        keyword_sets=(
            ("configuracion", "global"),
            ("ajustes", "globales"),
        ),
    ),
    IntentTriggerDefinition(
        intent=MetaTuningIntent.RULE,
        exact_phrases=(
            "a partir de ahora",
            "de ahora en adelante",
            "recuerda esta regla",
            "recuerda la regla",
            "agrega una regla",
            "anade una regla",
            "nueva regla",
            "guarda esta regla",
            "aumentar capacidades",
            "aumenta tus capacidades",
            "nueva capacidad",
            "aprende que",
            "haz que el coach sea",
            "haz que el advisor sea",
            "quiero que el coach",
            "quiero que el advisor",
            "se mas",
            "no me recomiendes",
            "descarta siempre",
            "prioriza siempre",
        ),
        keyword_sets=(),
    ),
    IntentTriggerDefinition(
        intent=MetaTuningIntent.PROMPT,
        exact_phrases=(
            "cambia tu prompt",
            "mejora tu prompt",
            "cambia tu tono",
            "habla mas rapido",
            "se mas breve",
            "modo tactico",
        ),
        keyword_sets=(),
    ),
    IntentTriggerDefinition(
        intent=MetaTuningIntent.RAG,
        exact_phrases=(
            "registra el dato",
            "registra este dato",
            "agrega a la base de datos",
            "guarda que el objeto",
            "registra que",
            "guarda que el rifle",
            "guarda que la bala",
        ),
        keyword_sets=(),
    ),
)

CATEGORY_TRIGGERS: Tuple[CategoryTriggerDefinition, ...] = (
    CategoryTriggerDefinition(
        category=MetaTuningCategory.LOOT,
        keywords=frozenset({"loot", "inventario", "mochila", "alijo", "objetos"}),
    ),
    CategoryTriggerDefinition(
        category=MetaTuningCategory.COMBAT,
        keywords=frozenset({"combate", "pelea", "disparo", "arma", "balas"}),
    ),
    CategoryTriggerDefinition(
        category=MetaTuningCategory.VOICE,
        keywords=frozenset({"voz", "audio", "habla", "rapido", "breve"}),
    ),
)

RULE_PREFIXES: Tuple[str, ...] = (
    "a partir de ahora",
    "de ahora en adelante",
    "recuerda esta regla",
    "agrega una regla",
    "aprende que",
)

VAGUE_STEMS: Tuple[str, ...] = (
    "mas inteligente",
    "mejor con el loot",
    "ayudame mejor",
    "quiero que seas mejor",
    "optimiza todo",
    "se mas pro",
    "ayudame mas",
    "mejora tu comportamiento",
)

VAGUE_KEYWORDS: FrozenSet[str] = frozenset({
    "mejor", "rapido", "inteligente", "bueno", "loot", "combate"
})

TACTICAL_QUALIFIERS: FrozenSet[str] = frozenset({
    "tier", "f8", "f9", "salome", "koen", "morado", "dorado", "m80"
})

PROVIDER_MAPPINGS: Tuple[ProviderMapping, ...] = (
    ProviderMapping(provider_id="nvidia", label="NVIDIA NIM"),
    ProviderMapping(provider_id="gemini", label="Gemini Vision"),
)

FACT_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("weapon", ("rifle", "arma", "pistola")),
    ("ammo", ("bala", "municion")),
    ("loot", ("loot", "objeto")),
)
