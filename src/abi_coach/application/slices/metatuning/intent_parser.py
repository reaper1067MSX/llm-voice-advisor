"""Intent Parser for Conversational Meta-Tuning (<100 LOC)."""
import re
import time
from typing import Optional
from abi_coach.domain.entities import metatuning_records as mr
from abi_coach.domain.entities.intent_lexicon import (
    CATEGORY_TRIGGERS, FACT_KEYWORDS, INTENT_TRIGGERS,
    PROVIDER_MAPPINGS, RULE_PREFIXES, TACTICAL_QUALIFIERS,
    VAGUE_KEYWORDS, VAGUE_STEMS, TextNormalizer,
)
from abi_coach.domain.enums.metatuning_enums import MetaTuningCategory, MetaTuningIntent


class IntentParser:
    """Parses user intents, vagueness, configuration changes, and rules using domain lexicons."""

    def __init__(self) -> None:
        self._norm = TextNormalizer()

    def detect_intent(self, prompt: str) -> Optional[MetaTuningIntent]:
        p, tokens = self._norm.normalize(prompt), self._norm.tokenize(prompt)
        for trigger in INTENT_TRIGGERS:
            if any(phrase in p for phrase in trigger.exact_phrases):
                return trigger.intent
            if any(all(k in tokens for k in kset) for kset in trigger.keyword_sets):
                return trigger.intent
        return None

    def is_vague(self, prompt: str) -> bool:
        p = self._norm.normalize(prompt)
        if any(s in p for s in VAGUE_STEMS):
            return True
        words = p.split()
        if len(words) <= 7 and any(x in words for x in VAGUE_KEYWORDS):
            has_digits = any(c.isdigit() for c in p)
            has_qualifier = any(k in p for k in TACTICAL_QUALIFIERS)
            return not (has_digits or has_qualifier)
        return False

    def is_cancellation(self, text: str) -> bool:
        return mr.is_cancellation_phrase(text)

    def detect_category(self, prompt: str) -> MetaTuningCategory:
        tokens = self._norm.tokenize(prompt)
        for cat_def in CATEGORY_TRIGGERS:
            if tokens & cat_def.keywords:
                return cat_def.category
        return MetaTuningCategory.GENERAL

    def parse_config(self, prompt: str) -> Optional[mr.ParsedConfig]:
        p = self._norm.normalize(prompt)
        for v_name, v_id in mr.VOICE_MAP.items():
            nv = self._norm.normalize(v_name)
            if f"voz a {nv}" in p or f"voz de {nv}" in p:
                return mr.ParsedConfig(["speaker", "voice"], v_id, f"Cambié la voz del sistema a {v_name.title()} ({v_id}).", "speaker.voice")
        if m := re.search(r"(?:tecla|ptt|push to talk)\s+(?:a\s+|en\s+)?(f[1-9]|f1[0-2])\b", p):
            key = m.group(1).lower()
            return mr.ParsedConfig(["listener", "ptt_key"], key, f"Cambié la tecla de Push-to-Talk a [{key.upper()}].", "listener.ptt_key")
        for mapping in PROVIDER_MAPPINGS:
            prov = mapping.provider_id
            if prov in p and ("proveedor" in p or f"usar {prov}" in p):
                return mr.ParsedConfig(["llm", "provider"], prov, f"Cambié el proveedor de Inteligencia Artificial a {mapping.label}.", "llm.provider")
        return None

    def parse_rule(self, prompt: str) -> mr.ParsedRule:
        p_norm, clean = self._norm.normalize(prompt), prompt
        for pfx in RULE_PREFIXES:
            if pfx in p_norm:
                clean = prompt[p_norm.find(pfx) + len(pfx):].strip().lstrip(",:.- ")
                break
        title = " ".join(clean.split()[:5]).title() if len(clean) > 40 else (clean.title() or "Regla de Comportamiento")
        slug = "".join(c if c.isalnum() else "_" for c in title.lower())[:30].strip("_")
        return mr.ParsedRule(title, slug, clean, "Aplicar en cada interacción relevante.")

    def parse_clarification_resolution(self, text: str, category: str = "general") -> mr.ParsedRule:
        r, tokens = self._norm.normalize(text), self._norm.tokenize(text)
        for rule in mr.RESOLUTION_RULES:
            if any(self._norm.normalize(k) in r or self._norm.normalize(k) in tokens for k in rule.keywords):
                return mr.ParsedRule(rule.title, rule.slug, rule.what, rule.learned)
        return mr.ParsedRule(
            f"Regla Personalizada: {category.title()}", f"{category}_{int(time.time())}",
            f"Regla establecida: {text.strip()}", "Comportamiento calibrado a petición del jugador.",
        )

    def parse_rag_fact(self, prompt: str) -> mr.ParsedFact:
        tokens, cat = self._norm.tokenize(prompt), "equipment"
        for c_name, kws in FACT_KEYWORDS:
            if tokens & set(kws):
                cat = c_name
                break
        return mr.ParsedFact(prompt[:40].strip(), cat, prompt.strip())


# Backward compatibility aliases
CANCELLATION_PHRASES = mr.CANCELLATION_PHRASES
RESOLUTION_RULES = mr.RESOLUTION_RULES
VOICE_MAP = mr.VOICE_MAP
ParsedConfig, ParsedFact, ParsedRule = mr.ParsedConfig, mr.ParsedFact, mr.ParsedRule
