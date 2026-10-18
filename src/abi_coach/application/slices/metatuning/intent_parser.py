"""Intent Parser for Conversational Meta-Tuning (<100 LOC)."""

import re
import time
from typing import Optional, Tuple
from abi_coach.domain.entities.metatuning_records import (
    CANCELLATION_PHRASES, RESOLUTION_RULES, VOICE_MAP,
    ParsedConfig, ParsedFact, ParsedRule, is_cancellation_phrase,
)
from abi_coach.domain.enums.metatuning_enums import MetaTuningCategory, MetaTuningIntent

_INTENT_PATTERNS = (
    (MetaTuningIntent.CONFIG, ("configuración global", "configuracion global", "ajustes globales", "cambiar configuración", "cambiar configuracion")),
    (MetaTuningIntent.RULE, ("a partir de ahora", "de ahora en adelante", "recuerda esta regla", "recuerda la regla", "agrega una regla", "añade una regla", "nueva regla", "guarda esta regla", "aumentar capacidades", "aumenta tus capacidades", "nueva capacidad", "aprende que", "haz que el coach sea", "haz que el advisor sea", "quiero que el coach", "quiero que el advisor", "sé más", "se mas", "no me recomiendes", "descarta siempre", "prioriza siempre")),
    (MetaTuningIntent.PROMPT, ("cambia tu prompt", "mejora tu prompt", "cambia tu tono", "habla más rápido", "habla mas rapido", "sé más breve", "se mas breve", "modo táctico", "modo tactico")),
    (MetaTuningIntent.RAG, ("registra el dato", "registra este dato", "agrega a la base de datos", "guarda que el objeto", "registra que", "guarda que el rifle", "guarda que la bala")),
)
_CATEGORY_PATTERNS = (
    (MetaTuningCategory.LOOT, ("loot", "inventario", "mochila", "alijo", "objetos")),
    (MetaTuningCategory.COMBAT, ("combate", "pelea", "disparo", "arma", "balas")),
    (MetaTuningCategory.VOICE, ("voz", "audio", "habla", "rápido", "rapido", "breve")),
)


class IntentParser:
    """Parses user intents, vagueness, configuration changes, and rules."""

    def detect_intent(self, prompt: str) -> Optional[str]:
        p = prompt.strip().lower()
        for intent, patterns in _INTENT_PATTERNS:
            if any(t in p for t in patterns):
                return intent
        return None

    def is_vague(self, prompt: str) -> bool:
        p = prompt.strip().lower()
        if any(s in p for s in ("más inteligente", "mas inteligente", "mejor con el loot", "ayúdame mejor", "ayudame mejor", "quiero que seas mejor", "optimiza todo", "sé más pro", "se mas pro", "ayúdame más", "ayudame mas", "mejora tu comportamiento")):
            return True
        w = p.split()
        if len(w) <= 7 and any(x in w for x in ("mejor", "rápido", "inteligente", "bueno", "loot", "combate")):
            return not (any(c.isdigit() for c in p) or any(k in p for k in ("tier", "f8", "f9", "salome", "salomé", "koen", "morado", "dorado", "m80")))
        return False

    def is_cancellation(self, text: str) -> bool:
        return is_cancellation_phrase(text)

    def detect_category(self, prompt: str) -> str:
        p = prompt.strip().lower()
        for category, patterns in _CATEGORY_PATTERNS:
            if any(w in p for w in patterns):
                return category
        return MetaTuningCategory.GENERAL

    def parse_config(self, prompt: str) -> Optional[ParsedConfig]:
        p = prompt.lower()
        for v_name, v_id in VOICE_MAP.items():
            if f"voz a {v_name}" in p or f"voz de {v_name}" in p:
                return ParsedConfig(["speaker", "voice"], v_id, f"Cambié la voz del sistema a {v_name.title()} ({v_id}).", "speaker.voice")
        if ptt := re.search(r"(?:tecla|ptt|push to talk)\s+(?:a\s+|en\s+)?(f[1-9]|f1[0-2])\b", p):
            k = ptt.group(1).lower()
            return ParsedConfig(["listener", "ptt_key"], k, f"Cambié la tecla de Push-to-Talk a [{k.upper()}].", "listener.ptt_key")
        for prov, label in (("nvidia", "NVIDIA NIM"), ("gemini", "Gemini Vision")):
            if prov in p and ("proveedor" in p or f"usar {prov}" in p):
                return ParsedConfig(["llm", "provider"], prov, f"Cambié el proveedor de Inteligencia Artificial a {label}.", "llm.provider")
        return None

    def parse_rule(self, prompt: str) -> ParsedRule:
        p_lower, clean = prompt.lower().strip(), prompt
        for pfx in ("a partir de ahora", "de ahora en adelante", "recuerda esta regla", "agrega una regla", "aprende que"):
            if pfx in p_lower:
                clean = prompt[p_lower.find(pfx) + len(pfx):].strip().lstrip(",:.- ")
                break
        title = " ".join(clean.split()[:5]).title() if len(clean) > 40 else (clean.title() or "Regla de Comportamiento")
        slug = "".join(c if c.isalnum() else "_" for c in title.lower())[:30].strip("_")
        return ParsedRule(title, slug, clean, "Aplicar en cada interacción relevante.")

    def parse_clarification_resolution(self, text: str, category: str = "general") -> ParsedRule:
        r = text.strip().lower()
        for kws, t, s, w, l in RESOLUTION_RULES:
            if any(k in r for k in kws):
                return ParsedRule(t, s, w, l)
        return ParsedRule(
            f"Regla Personalizada: {category.title()}", f"{category}_{int(time.time())}",
            f"Regla establecida: {text.strip()}", "Comportamiento calibrado a petición del jugador.",
        )

    def parse_rag_fact(self, prompt: str) -> ParsedFact:
        p = prompt.lower()
        cat = "weapon" if any(w in p for w in ("rifle", "arma", "pistola")) else ("ammo" if any(w in p for w in ("bala", "municion", "munición")) else ("loot" if any(w in p for w in ("loot", "objeto")) else "equipment"))
        return ParsedFact(prompt[:40].strip(), cat, prompt.strip())


__all__ = [
    "CANCELLATION_PHRASES", "IntentParser", "ParsedConfig", "ParsedFact",
    "ParsedRule", "RESOLUTION_RULES", "VOICE_MAP",
]
