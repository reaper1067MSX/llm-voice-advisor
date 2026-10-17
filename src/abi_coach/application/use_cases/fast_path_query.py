"""Zero-LLM Fast Path Query Use Case for instant numerical and stat retrieval."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.application.slices.archetypes.manager import ArchetypeManager
from abi_coach.application.slices.tactical_rag.rag import KnowledgeRAG
from abi_coach.application.use_cases import CoachResponse

STAT_TRIGGERS: List[str] = [
    "qué penetración", "que penetracion", "cuánta penetración", "cuanta penetracion",
    "cuánto daño", "cuanto dano", "cuánto de daño", "cuanto de dano",
    "qué daño", "que dano", "qué tier", "que tier", "de qué tier", "de que tier",
    "cuánto vale", "cuanto vale", "a cuánto se vende", "a cuanto se vende",
    "precio de", "estadísticas de", "estadisticas de", "stats de",
]

GENERIC_WORDS = {
    "que", "qué", "cual", "cuál", "cuanto", "cuánto", "cuanta", "cuánta",
    "tiene", "tienen", "es", "son", "de", "la", "el", "los", "las", "un", "una",
    "penetracion", "penetración", "dano", "daño", "tier", "nivel", "vale",
    "vende", "precio", "estadisticas", "estadísticas", "stats", "base",
    "bala", "balas", "municion", "munición", "arma", "rifle", "objeto",
}


def _extract_stats(entry: Dict[str, Any]) -> Dict[str, Any]:
    if entry.get("data_json"):
        try:
            return json.loads(entry["data_json"])
        except Exception:
            return {}
    if isinstance(entry.get("facets"), dict):
        return entry["facets"]
    if entry.get("facets_json"):
        try:
            return json.loads(entry["facets_json"])
        except Exception:
            return {}
    return {}


class FastPathQueryUseCase:
    """Encapsulates zero-LLM factual retrieval (< 2ms) using local SQLite RAG & entity lookup."""

    def __init__(
        self,
        rag: Optional[KnowledgeRAG] = None,
        archetype_mgr: Optional[ArchetypeManager] = None,
        history_mgr: Optional[ConversationHistoryManager] = None,
    ) -> None:
        self.rag = rag
        self.archetype_mgr = archetype_mgr
        self.history_mgr = history_mgr

    def execute(self, prompt: str, game_id: str = "generic") -> Optional[CoachResponse]:
        """Attempt immediate zero-LLM local factual retrieval for direct stat queries."""
        if (not self.rag and not self.archetype_mgr) or not prompt:
            return None

        p_lower = prompt.lower().strip()
        if not any(trigger in p_lower for trigger in STAT_TRIGGERS):
            return None

        query_words = [
            w.lower()
            for w in re.findall(r"[A-Za-z0-9_\-\.]+", prompt)
            if len(w) > 1 and w.lower() not in GENERIC_WORDS
        ]

        def _matches(entry: Dict[str, Any]) -> bool:
            if not query_words:
                return True
            haystack = f"{entry.get('title', '')} {entry.get('entity_key', '')}".lower()
            return any(qw in haystack for qw in query_words)

        gid = game_id or "generic"
        results = self.rag.search(prompt, game=gid, limit=2) if self.rag else []

        item: Optional[Dict[str, Any]] = None
        data: Dict[str, Any] = {}
        for r in results:
            if _matches(r):
                d = _extract_stats(r)
                if ("penetration" in d and "damage" in d) or "approx_value" in d:
                    item, data = r, d
                    break

        if item is None and self.archetype_mgr:
            v2_results = self.archetype_mgr.search_entities(prompt, context_id=gid, limit=2)
            for r in v2_results:
                if _matches(r):
                    d = _extract_stats(r)
                    if ("penetration" in d and "damage" in d) or "approx_value" in d:
                        item, data = r, d
                        break
            if item is None:
                for r in v2_results:
                    if _matches(r):
                        item, data = r, _extract_stats(r)
                        break

        if item is None:
            for r in results:
                if _matches(r):
                    item, data = r, _extract_stats(r)
                    break

        if item is None:
            return None

        title = item.get("title", "Objeto")
        if "penetration" in data and "damage" in data:
            tier_str = f", nivel Tier {data.get('tier', '?')}" if "tier" in data else ""
            spoken = f"La {title} tiene {data['penetration']} de penetración y {data['damage']} de daño base{tier_str}."
        elif "approx_value" in data:
            spoken = f"El {title} tiene un valor estimado de mercado de {data['approx_value']:,} Koens."
        else:
            spoken = item.get("summary", "")

        if self.history_mgr:
            self.history_mgr.add_user_coach(prompt, spoken)

        return CoachResponse(
            spoken_text=spoken,
            report_path=None,
            input_tokens=0,
            output_tokens=0,
            latency_ms=1.5,
        )
