"""Verbal context switch trigger detector."""

from __future__ import annotations

import re
from typing import Optional

from abi_coach.domain.entities.context_switch_records import (
    CONTEXT_PATTERNS,
    ContextSwitchRequest,
)


class ContextSwitchDetector:
    """Analyzes spoken prompts for explicit game/advisor context switch intent."""

    def detect(self, prompt: str) -> Optional[ContextSwitchRequest]:
        """Detect context switch trigger phrases and map to a target game context."""
        p = (prompt or "").strip().lower()
        if not p:
            return None

        for pat in CONTEXT_PATTERNS:
            m = re.search(pat, p, re.IGNORECASE)
            if not m:
                continue
            raw = m.group(1).strip().strip(".?!,")
            if not raw:
                continue
            cl = raw.lower()

            if any(x in cl for x in ("advisor", "generico", "genérico", "general", "universal")):
                return ContextSwitchRequest(
                    target_game="generic",
                    display_name="Game Advisor Universal",
                    raw_utterance=prompt,
                )
            if cl in ("abi", "arena breakout", "arena breakout infinite", "arena breakout: infinite", "coach"):
                return ContextSwitchRequest(
                    target_game="abi",
                    display_name="Arena Breakout: Infinite",
                    raw_utterance=prompt,
                )
            if any(x in cl for x in ("once human", "oncehuman", "once-human", "once_human")):
                return ContextSwitchRequest(
                    target_game="once_human",
                    display_name="Once Human",
                    raw_utterance=prompt,
                )
            canon = re.sub(r"[^a-z0-9]+", "_", cl).strip("_")
            return ContextSwitchRequest(
                target_game=canon,
                display_name=raw.title(),
                raw_utterance=prompt,
            )
        return None
