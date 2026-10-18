"""Intent Parser for Conversational Meta-Tuning (<100 LOC)."""

from dataclasses import dataclass
import re
import time
from typing import Any, List, Optional, Tuple

@dataclass(frozen=True)
class ParsedConfig:
    key_path: List[str]; value: Any; message: str; key_name: str

@dataclass(frozen=True)
class ParsedRule:
    title: str; slug: str; what: str; learned: str

@dataclass(frozen=True)
class ParsedFact:
    title: str; category: str; summary: str

CANCELLATION_PHRASES = ("cancela", "cancelar", "olvídalo", "olvidalo", "no importa")
VOICE_MAP = {
    "salome": "es-CO-SalomeNeural", "salomé": "es-CO-SalomeNeural", "elvira": "es-ES-ElviraNeural", "ximena": "es-ES-XimenaNeural",
    "camila": "es-PE-CamilaNeural", "paloma": "es-US-PalomaNeural", "dalia": "es-MX-DaliaNeural", "elena": "es-AR-ElenaNeural", "catalina": "es-CL-CatalinaNeural",
}
RESOLUTION_RULES: List[Tuple[Tuple[str, ...], str, str, str, str]] = [
    (("casilla", "valor"), "Prioridad de Loot por Casilla", "loot_value_per_slot", "Priorizar estrictamente objetos con mayor valor económico estimado por casilla de inventario.", "Descartar objetos voluminosos de bajo valor unitario para maximizar rentabilidad."),
    (("morado", "dorado", "tier"), "Filtro de Objetos de Alto Tier", "high_tier_loot_only", "Filtrar y alertar únicamente sobre objetos morados, dorados o de Tier 4 o superior.", "Ignorar loot común o gris para acelerar el ritmo de juego."),
    (("contrato", "craft", "mision"), "Objetos de Contratos y Crafteo", "quest_craft_items", "Destacar objetos requeridos para contratos de comerciantes o materiales raros de crafteo.", "Notificar inmediatamente cuando un objeto coincida con contratos activos."),
    (("penetracion", "penetración", "blindaje"), "Prioridad Balística: Penetración Máxima", "max_penetration", "Recomendar exclusivamente munición con penetración capaz de perforar blindajes pesados.", "Evitar munición de daño a extremidades cuando el objetivo porte armadura Tier 5 o 6."),
    (("retroceso", "build"), "Builds de Bajo Retroceso", "low_recoil_builds", "Priorizar estabilidad y reducción de retroceso vertical y horizontal en modificaciones de armas.", "Favorecer empuñaduras y bocachas de compensación sobre ergonomía pura."),
]

class IntentParser:
    """Parses user intents, vagueness, configuration changes, and rules."""

    def detect_intent(self, prompt: str) -> Optional[str]:
        p = prompt.strip().lower()
        if any(t in p for t in ("configuración global", "configuracion global", "ajustes globales", "cambiar configuración", "cambiar configuracion")): return "config"
        if any(t in p for t in ("a partir de ahora", "de ahora en adelante", "recuerda esta regla", "recuerda la regla", "agrega una regla", "añade una regla", "nueva regla", "guarda esta regla", "aumentar capacidades", "aumenta tus capacidades", "nueva capacidad", "aprende que", "haz que el coach sea", "haz que el advisor sea", "quiero que el coach", "quiero que el advisor", "sé más", "se mas", "no me recomiendes", "descarta siempre", "prioriza siempre")): return "rule"
        if any(t in p for t in ("cambia tu prompt", "mejora tu prompt", "cambia tu tono", "habla más rápido", "habla mas rapido", "sé más breve", "se mas breve", "modo táctico", "modo tactico")): return "prompt"
        if any(t in p for t in ("registra el dato", "registra este dato", "agrega a la base de datos", "guarda que el objeto", "registra que", "guarda que el rifle", "guarda que la bala")): return "rag"
        return None

    def is_vague(self, prompt: str) -> bool:
        p = prompt.strip().lower()
        if any(s in p for s in ("más inteligente", "mas inteligente", "mejor con el loot", "ayúdame mejor", "ayudame mejor", "quiero que seas mejor", "optimiza todo", "sé más pro", "se mas pro", "ayúdame más", "ayudame mas", "mejora tu comportamiento")): return True
        w = p.split()
        if len(w) <= 7 and any(x in w for x in ("mejor", "rápido", "inteligente", "bueno", "loot", "combate")):
            return not (any(c.isdigit() for c in p) or any(k in p for k in ("tier", "f8", "f9", "salome", "salomé", "koen", "morado", "dorado", "m80")))
        return False

    def is_cancellation(self, text: str) -> bool:
        c = text.strip().lower().strip(".?!,¡¿")
        return c in CANCELLATION_PHRASES or "no importa" in c or bool(set(re.findall(r"[a-záéíóúñ]+", c)) & {"cancela", "cancelar", "olvídalo", "olvidalo"})

    def detect_category(self, prompt: str) -> str:
        p = prompt.strip().lower()
        if any(w in p for w in ("loot", "inventario", "mochila", "alijo", "objetos")): return "loot"
        if any(w in p for w in ("combate", "pelea", "disparo", "arma", "balas")): return "combat"
        if any(w in p for w in ("voz", "audio", "habla", "rápido", "rapido", "breve")): return "voice"
        return "general"

    def parse_config(self, prompt: str) -> Optional[ParsedConfig]:
        p = prompt.lower()
        for v_name, v_id in VOICE_MAP.items():
            if f"voz a {v_name}" in p or f"voz de {v_name}" in p:
                return ParsedConfig(["speaker", "voice"], v_id, f"Cambié la voz del sistema a {v_name.title()} ({v_id}).", "speaker.voice")
        if ptt := re.search(r"(?:tecla|ptt|push to talk)\s+(?:a\s+|en\s+)?(f[1-9]|f1[0-2])\b", p):
            k = ptt.group(1).lower()
            return ParsedConfig(["listener", "ptt_key"], k, f"Cambié la tecla de Push-to-Talk a [{k.upper()}].", "listener.ptt_key")
        if "nvidia" in p and ("proveedor" in p or "usar nvidia" in p):
            return ParsedConfig(["llm", "provider"], "nvidia", "Cambié el proveedor de Inteligencia Artificial a NVIDIA NIM.", "llm.provider")
        if "gemini" in p and ("proveedor" in p or "usar gemini" in p):
            return ParsedConfig(["llm", "provider"], "gemini", "Cambié el proveedor de Inteligencia Artificial a Gemini Vision.", "llm.provider")
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
            if any(k in r for k in kws): return ParsedRule(t, s, w, l)
        return ParsedRule(f"Regla Personalizada: {category.title()}", f"{category}_{int(time.time())}", f"Regla establecida: {text.strip()}", "Comportamiento calibrado a petición del jugador.")

    def parse_rag_fact(self, prompt: str) -> ParsedFact:
        p = prompt.lower()
        cat = "weapon" if any(w in p for w in ("rifle", "arma", "pistola")) else ("ammo" if any(w in p for w in ("bala", "municion", "munición")) else ("loot" if any(w in p for w in ("loot", "objeto")) else "equipment"))
        return ParsedFact(prompt[:40].strip(), cat, prompt.strip())
