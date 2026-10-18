"""Clarification Finite State Machine with 60s TTL for Meta-Tuning (<100 LOC)."""

from dataclasses import dataclass, field
import re
import threading
import time
from typing import Any, Optional, Tuple

CANCELLATION_PHRASES = ("cancela", "cancelar", "olvídalo", "olvidalo", "no importa")
CLARIFICATION_TTL_SEC = 60.0

CONFIRMATION_RULES = (
    (("casilla", "valor"), "Prioridad de Loot por Casilla", "loot_value_per_slot", "Priorizar estrictamente objetos con mayor valor económico estimado por casilla de inventario.", "Descartar objetos voluminosos de bajo valor unitario para maximizar rentabilidad."),
    (("morado", "dorado", "tier"), "Filtro de Objetos de Alto Tier", "high_tier_loot_only", "Filtrar y alertar únicamente sobre objetos morados, dorados o de Tier 4 o superior.", "Ignorar loot común o gris para acelerar el ritmo de juego."),
    (("contrato", "craft", "mision"), "Objetos de Contratos y Crafteo", "quest_craft_items", "Destacar objetos requeridos para contratos de comerciantes o materiales raros de crafteo.", "Notificar inmediatamente cuando un objeto coincida con contratos activos."),
    (("penetracion", "penetración", "blindaje"), "Prioridad Balística: Penetración Máxima", "max_penetration", "Recomendar exclusivamente munición con penetración capaz de perforar blindajes pesados.", "Evitar munición de daño a extremidades cuando el objetivo porte armadura Tier 5 o 6."),
    (("retroceso", "build"), "Builds de Bajo Retroceso", "low_recoil_builds", "Priorizar estabilidad y reducción de retroceso vertical y horizontal en modificaciones de armas.", "Favorecer empuñaduras y bocachas de compensación sobre ergonomía pura."),
)


@dataclass
class ClarificationState:
    """State of a pending clarification loop with 60s TTL."""
    original_prompt: str
    context_id: str = "generic"
    category: str = "general"
    created_at: float = field(default_factory=time.time)

    @property
    def timestamp(self) -> float: return self.created_at
    def get(self, key: str, default: Any = None) -> Any: return self.created_at if key == "timestamp" else getattr(self, key, default)
    def __getitem__(self, key: str) -> Any: return self.created_at if key == "timestamp" else getattr(self, key)


@dataclass(frozen=True)
class ClarificationResolution:
    title: str; slug: str; what: str; learned: str


def is_cancellation_phrase(text: str) -> bool:
    clean = text.strip().lower().strip(".?!,¡¿")
    if clean in CANCELLATION_PHRASES or "no importa" in clean: return True
    return bool(set(re.findall(r"[a-záéíóúñ]+", clean)) & {"cancela", "cancelar", "olvídalo", "olvidalo"})


class ClarificationFSM:
    """Thread-safe finite state machine managing clarification transitions and TTL (<100 LOC)."""

    def __init__(self, ttl_sec: float = CLARIFICATION_TTL_SEC) -> None:
        self.ttl_sec = ttl_sec
        self.pending: Optional[ClarificationState] = None
        self._lock = threading.RLock()

    @property
    def has_pending(self) -> bool:
        with self._lock: return self.pending is not None

    def start(self, prompt: str, context_id: str = "generic", category: str = "general") -> ClarificationState:
        with self._lock:
            self.pending = ClarificationState(prompt, context_id, category, time.time())
            return self.pending

    def start_clarification(self, prompt: str, context_id: str = "generic", category: str = "general") -> ClarificationState:
        return self.start(prompt, context_id, category)

    def is_expired(self, now: Optional[float] = None, auto_reset: bool = False) -> bool:
        with self._lock:
            if not self.pending: return False
            created = getattr(self.pending, "created_at", None) or getattr(self.pending, "timestamp", None)
            if created is None and isinstance(self.pending, dict):
                created = self.pending.get("created_at") or self.pending.get("timestamp")
            expired = ((time.time() if now is None else now) - float(created)) > self.ttl_sec if created else False
            if expired and auto_reset: self.pending = None
            return expired

    def is_cancellation(self, text: str) -> bool:
        return is_cancellation_phrase(text)

    def resolve(self, text: str) -> Tuple[Optional[ClarificationState], ClarificationResolution]:
        with self._lock:
            state = self.pending
            self.pending = None
            category = state.category if state else "general"
            for kws, title, slug, what, learned in CONFIRMATION_RULES:
                if any(k in text.lower() for k in kws):
                    return state, ClarificationResolution(title, slug, what, learned)
            return state, ClarificationResolution(
                f"Regla Personalizada: {category.title()}", f"{category}_{int(time.time())}",
                f"Regla establecida: {text.strip()}", "Comportamiento calibrado a petición del jugador.",
            )

    def reset(self) -> None:
        with self._lock: self.pending = None

    def clear(self) -> None:
        self.reset()
