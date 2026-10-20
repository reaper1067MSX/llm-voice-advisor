"""Domain Enums for Conversational Meta-Tuning."""

from enum import StrEnum


class MetaTuningIntent(StrEnum):
    """Supported user tuning intent categories."""

    CONFIG = "config"
    RULE = "rule"
    PROMPT = "prompt"
    RAG = "rag"


class MetaTuningCategory(StrEnum):
    """Tactical categories for rules and clarifications."""

    LOOT = "loot"
    COMBAT = "combat"
    VOICE = "voice"
    GENERAL = "general"


class MetaTuningAction(StrEnum):
    """State transition outcomes of meta-tuning operations."""

    CLARIFICATION_NEEDED = "clarification_needed"
    RULE_SAVED = "rule_saved"
    CONFIG_UPDATED = "config_updated"
    PROMPT_UPDATED = "prompt_updated"
    RAG_INGESTED = "rag_ingested"
    CANCELLED = "cancelled"


__all__ = [
    "MetaTuningIntent",
    "MetaTuningCategory",
    "MetaTuningAction",
]
