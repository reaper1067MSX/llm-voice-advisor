"""System prompt registry and dynamic template repository using Dependency Injection."""

from __future__ import annotations

import re
from typing import Callable, Dict, Optional

from abi_coach.infrastructure.resources.prompts.abi import SYSTEM_INSTRUCTION_ABI
from abi_coach.infrastructure.resources.prompts.generic import SYSTEM_INSTRUCTION_GENERIC
from abi_coach.infrastructure.resources.prompts.once_human import SYSTEM_INSTRUCTION_ONCE_HUMAN

# Backward compatibility aliases
ABI_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_ABI
COACH_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_ABI
GENERIC_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_GENERIC
ONCE_HUMAN_SYSTEM_INSTRUCTION = SYSTEM_INSTRUCTION_ONCE_HUMAN

DEFAULT_TEMPLATES: Dict[str, str] = {
    "abi": SYSTEM_INSTRUCTION_ABI,
    "once_human": SYSTEM_INSTRUCTION_ONCE_HUMAN,
    "generic": SYSTEM_INSTRUCTION_GENERIC,
}


def _canonicalize_game_key(name: str) -> str:
    clean = (name or "").lower().strip()
    if clean in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
        return "abi"
    if clean in ("once_human", "oncehuman", "once-human", "once human"):
        return "once_human"
    if clean:
        return re.sub(r"[^a-z0-9]+", "_", clean).strip("_")
    return "generic"


class PromptTemplateRegistry:
    """Pure template registry for system instructions injected via Dependency Injection."""

    def __init__(
        self,
        templates: Optional[Dict[str, str]] = None,
        fallback_template: Optional[str] = None,
        loader: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._templates: Dict[str, str] = dict(templates or DEFAULT_TEMPLATES)
        self._fallback = fallback_template or SYSTEM_INSTRUCTION_GENERIC
        self._loader = loader

    def get_preset(self, game_name: str) -> str:
        """Resolve system prompt preset for a specific game/context."""
        key = _canonicalize_game_key(game_name)
        if key in self._templates:
            return self._templates[key]
        if self._loader:
            loaded = self._loader(game_name)
            if loaded:
                self._templates[key] = loaded
                return loaded
        return self._templates.get("generic", self._fallback)

    def register_preset(self, game_name: str, template: str) -> None:
        """Register or override a prompt template."""
        key = _canonicalize_game_key(game_name)
        self._templates[key] = template

    def get_template(self, context_id: str) -> str:
        """Alias for get_preset."""
        return self.get_preset(context_id)


_DEFAULT_REGISTRY = PromptTemplateRegistry()


def load_preset(game_name: str) -> str:
    """Convenience functional loader delegating to the default DI registry."""
    return _DEFAULT_REGISTRY.get_preset(game_name)
