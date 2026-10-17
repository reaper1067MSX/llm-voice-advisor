"""Tactical Finite State Machine (FSM) & Voice Silence Interceptor."""

import re
import unicodedata
from typing import Optional

from abi_coach.domain.entities.tactical_state import TacticalState


def _normalize_text(text: str) -> str:
    """Normalize text removing accents, punctuation and excess whitespace."""
    nfkd = unicodedata.normalize("NFKD", text)
    cleaned = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    return " ".join(cleaned.split())


class TacticalFSM:
    """Finite State Machine tracking the gameplay situation and focus mode."""

    SILENCE_KEYWORDS = (
        "silencio de radio",
        "modo concentracion",
        "concentracion",
        "callate",
        "silencio",
        "silencio total",
        "guarda silencio",
        "silencio por favor",
        "no hables",
        "mute",
    )

    RESUME_KEYWORDS = (
        "reanuda",
        "reanudar",
        "companion activo",
        "vuelve",
        "habla",
        "desactiva silencio",
        "desactivar silencio",
        "cancela silencio",
        "termina concentracion",
        "termina silencio",
    )

    def __init__(self, initial_state: TacticalState = TacticalState.EXPLORING):
        self.state: TacticalState = initial_state
        self.previous_state: TacticalState = initial_state

    def transition_to(self, new_state: TacticalState) -> None:
        """Explicitly transition to a new tactical state."""
        if self.state != new_state:
            self.previous_state = self.state
            self.state = new_state

    def can_suggest_proactively(self) -> bool:
        """Check if proactive advice/chatter is allowed in the current state."""
        if self.state in (TacticalState.RADIO_SILENCE, TacticalState.COMBAT):
            return False
        return True

    def intercept_voice_command(self, prompt: str) -> Optional[str]:
        """Check if the user prompt is a fast-path command to toggle silence or report status.
        
        Returns:
            Immediate spoken confirmation string if matched, or None if normal query.
        """
        norm = _normalize_text(prompt)
        if not norm:
            return None

        # Check for radio silence activation
        for kw in self.SILENCE_KEYWORDS:
            # Match keyword as standalone phrase or start/end
            if norm == kw or norm.startswith(f"{kw} ") or norm.endswith(f" {kw}"):
                self.transition_to(TacticalState.RADIO_SILENCE)
                return "Copiado, silencio de radio activo. Concentración total."

        # Check for resume activation
        for kw in self.RESUME_KEYWORDS:
            if norm == kw or norm.startswith(f"{kw} ") or norm.endswith(f" {kw}"):
                target_state = (
                    self.previous_state
                    if self.previous_state != TacticalState.RADIO_SILENCE
                    else TacticalState.EXPLORING
                )
                self.transition_to(target_state)
                return "Entendido, canal abierto. Te cubro las espaldas."

        return None
