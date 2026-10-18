"""Focused unit tests for IntentParser and Domain Lexicon."""

from abi_coach.application.slices.metatuning.intent_parser import IntentParser
from abi_coach.domain.enums.metatuning_enums import MetaTuningCategory, MetaTuningIntent


def test_intent_parser_classification_and_heuristics():
    """Verify IntentParser detects intents and distinguishes vague from actionable prompts."""
    parser = IntentParser()

    assert parser.detect_intent("Configuración global cambia la voz a Salomé") == MetaTuningIntent.CONFIG
    assert parser.detect_intent("A partir de ahora prioriza siempre el loot morado") == MetaTuningIntent.RULE
    assert parser.detect_intent("Cambia tu prompt para ser más táctico") == MetaTuningIntent.PROMPT
    assert parser.detect_intent("Registra que el rifle MDR tiene 45 de daño") == MetaTuningIntent.RAG
    assert parser.detect_intent("¿Cómo está el clima?") is None

    assert parser.is_vague("Haz que el coach sea más inteligente con el loot") is True
    assert parser.is_vague("Ayúdame mejor") is True
    assert parser.is_vague("A partir de ahora solo avísame de munición Tier 4") is False
    assert parser.is_vague("Configuración global pon la tecla en F8") is False


def test_intent_parser_config_and_rule_parsing():
    """Verify IntentParser extracts parameters for config changes and rule observations."""
    parser = IntentParser()

    voice_cfg = parser.parse_config("cambiar configuración pon la voz a Elvira")
    assert voice_cfg is not None
    assert voice_cfg.key_path == ["speaker", "voice"]
    assert voice_cfg.value == "es-ES-ElviraNeural"

    ptt_cfg = parser.parse_config("cambiar ptt a f11")
    assert ptt_cfg is not None
    assert ptt_cfg.key_path == ["listener", "ptt_key"]
    assert ptt_cfg.value == "f11"

    provider_nvidia = parser.parse_config("usar nvidia como proveedor")
    assert provider_nvidia is not None
    assert provider_nvidia.key_path == ["llm", "provider"]
    assert provider_nvidia.value == "nvidia"

    provider_gemini = parser.parse_config("usar gemini como proveedor")
    assert provider_gemini is not None
    assert provider_gemini.key_path == ["llm", "provider"]
    assert provider_gemini.value == "gemini"

    assert parser.parse_config("pregunta no relacionada") is None

    parsed_rule = parser.parse_rule("A partir de ahora descarta siempre el loot gris")
    assert parsed_rule.what == "descarta siempre el loot gris"
    assert "Loot Gris" in parsed_rule.title
    assert parsed_rule.slug != ""

    assert parser.detect_category("optimiza mi alijo") == MetaTuningCategory.LOOT
    assert parser.detect_category("asistencia en pelea de arma corta") == MetaTuningCategory.COMBAT
    assert parser.detect_category("cambia el audio y habla breve") == MetaTuningCategory.VOICE
    assert parser.detect_category("otra cosa aleatoria") == MetaTuningCategory.GENERAL

    fact_weapon = parser.parse_rag_fact("El rifle M4A1 usa calibre 5.56")
    assert fact_weapon.category == "weapon"
    fact_ammo = parser.parse_rag_fact("La bala M80 perfora blindaje clase 4")
    assert fact_ammo.category == "ammo"
    fact_loot = parser.parse_rag_fact("El objeto León Dorado vale 150k")
    assert fact_loot.category == "loot"


def test_intent_parser_cancellation_and_resolution():
    """Verify IntentParser cancellation detection and clarification response resolution."""
    parser = IntentParser()

    assert parser.is_cancellation("cancela") is True
    assert parser.is_cancellation("olvídalo") is True
    assert parser.is_cancellation("no importa") is True
    assert parser.is_cancellation("¡Cancela por favor!") is True
    assert parser.is_cancellation("quiero continuar") is False

    rule_loot = parser.parse_clarification_resolution("Prioriza el valor por casilla", category="loot")
    assert rule_loot.slug == "loot_value_per_slot"

    rule_ammo = parser.parse_clarification_resolution("Penetración máxima contra blindajes", category="combat")
    assert rule_ammo.slug == "max_penetration"

    rule_custom = parser.parse_clarification_resolution("haz algo completamente personalizado", category="combat")
    assert "Personalizada" in rule_custom.title
