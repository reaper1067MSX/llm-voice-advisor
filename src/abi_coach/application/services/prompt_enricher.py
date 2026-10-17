"""Pipeline service for enriching system prompt templates with dynamic profiles."""

from __future__ import annotations

from typing import Any, List, Optional

from abi_coach.application.services.prompt_registry import PromptTemplateRegistry


class SystemPromptEnricherPipeline:
    """Orchestrates dynamic prompt enrichment across presets, archetypes, and player memory."""

    def __init__(self, registry: Optional[PromptTemplateRegistry] = None) -> None:
        self.registry = registry or PromptTemplateRegistry()

    def build_system_instruction(
        self,
        game_id: str,
        custom_instruction: Optional[str] = None,
        archetype_mgr: Optional[Any] = None,
        memory: Optional[Any] = None,
    ) -> str:
        """Compose the complete system instruction pipeline."""
        gid = game_id or "generic"

        if custom_instruction:
            base_prompt = custom_instruction
        else:
            base_prompt = self._resolve_base_prompt(gid, archetype_mgr)

        enrichments: List[str] = []
        if memory and hasattr(memory, "format_profile_for_prompt"):
            mem_profile = memory.format_profile_for_prompt(game=gid)
            if mem_profile:
                enrichments.append(mem_profile)

        if archetype_mgr and hasattr(archetype_mgr, "format_profile_for_prompt"):
            engram_rules = archetype_mgr.format_profile_for_prompt(context_id=gid)
            if engram_rules:
                enrichments.append(engram_rules)

        if not enrichments:
            return base_prompt

        return base_prompt + "\n\n" + "\n\n".join(enrichments)

    def _resolve_base_prompt(self, game_id: str, archetype_mgr: Optional[Any]) -> str:
        if game_id not in ("generic", "") and archetype_mgr and hasattr(archetype_mgr, "get_context"):
            ctx = archetype_mgr.get_context(game_id)
            if ctx and hasattr(archetype_mgr, "get_archetype"):
                arch = archetype_mgr.get_archetype(ctx.archetype_id)
                if arch and getattr(arch, "default_system_prompt", None):
                    return f"Eres un copiloto táctico para '{ctx.display_name}'.\n{arch.default_system_prompt}"
        return self.registry.get_preset(game_id)
