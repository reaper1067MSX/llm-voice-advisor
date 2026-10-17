"""Unit tests for PromptTemplateRegistry and SystemPromptEnricherPipeline."""

from unittest.mock import MagicMock

from abi_coach.application.services.prompt_enricher import SystemPromptEnricherPipeline
from abi_coach.application.services.prompt_registry import PromptTemplateRegistry


def test_prompt_registry_presets_and_custom_registration():
    """Verify registry resolves default presets and allows dynamic template registration."""
    registry = PromptTemplateRegistry()

    assert "Arena Breakout" in registry.get_preset("abi")
    assert "Once Human" in registry.get_preset("once_human")
    assert "Game Advisor" in registry.get_preset("generic")
    assert "Game Advisor" in registry.get_preset("unknown_game")

    registry.register_preset("cyberpunk", "Eres Johnny Silverhand.")
    assert registry.get_preset("cyberpunk") == "Eres Johnny Silverhand."


def test_prompt_enricher_pipeline_overrides_and_profiles():
    """Verify prompt enrichment with custom instruction, memory profile, and engram rules."""
    pipeline = SystemPromptEnricherPipeline()

    # Custom instruction overrides base preset
    custom = pipeline.build_system_instruction("abi", custom_instruction="Custom ABI Prompt")
    assert custom == "Custom ABI Prompt"

    # Dynamic memory and archetype profile enrichment
    mock_memory = MagicMock()
    mock_memory.format_profile_for_prompt.return_value = "[PERFIL]: Francotirador"
    mock_archetype = MagicMock()
    mock_archetype.get_context.return_value = None
    mock_archetype.format_profile_for_prompt.return_value = "[ENGRAM]: Usar suppressor"

    enriched = pipeline.build_system_instruction("abi", memory=mock_memory, archetype_mgr=mock_archetype)
    assert "[PERFIL]: Francotirador" in enriched
    assert "[ENGRAM]: Usar suppressor" in enriched
