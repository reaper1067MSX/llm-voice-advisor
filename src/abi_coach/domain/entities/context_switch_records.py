"""Domain records and patterns for context switching and detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ContextSwitchRequest:
    """Record representing a detected context switch intent."""

    target_game: str
    display_name: str
    archetype_id: Optional[str] = None
    confidence: float = 1.0
    raw_utterance: str = ""


CONTEXT_PATTERNS: Tuple[str, ...] = (
    r"(?:vamos a jugar|vamos a darle a|juguemos a|jugar a)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:cambiar a|cambia a|cambiemos a|cambiar al juego|cambia al juego)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:cambiar contexto a|cambia contexto a|conmutar a)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:inicia contexto para|iniciar contexto para|inicia el contexto de)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:pon el juego|cargar juego|cambia de juego a)\s+([a-zA-Z0-9_\s:-]+)",
    r"(?:activar modo|cambia a modo|cambiar a modo|modo)\s+(advisor|gen[eé]rico|abi|coach)",
)
