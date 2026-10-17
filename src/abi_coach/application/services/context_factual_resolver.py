"""Context factual resolver for zero-LLM deterministic stat and inventory lookup."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STAT_TRIGGERS: tuple[str, ...] = (
    "qué penetración", "que penetracion", "cuánta penetración", "cuanta penetracion",
    "cuánto daño", "cuanto dano", "cuánto de daño", "cuanto de dano",
    "qué daño", "que dano", "qué tier", "que tier", "de qué tier", "de que tier",
    "cuánto vale", "cuanto vale", "a cuánto se vende", "a cuanto se vende",
    "precio de", "estadísticas de", "estadisticas de", "stats de",
)

STOPWORDS: frozenset[str] = frozenset({
    "que", "qué", "cual", "cuál", "cuanto", "cuánto", "cuanta", "cuánta",
    "tiene", "tienen", "es", "son", "de", "la", "el", "los", "las", "un", "una",
    "penetracion", "penetración", "dano", "daño", "tier", "nivel", "vale",
    "vende", "precio", "estadisticas", "estadísticas", "stats", "base",
    "bala", "balas", "municion", "munición", "arma", "rifle", "objeto",
})


class ContextFactualResolver:
    """Encapsulates context-level factual knowledge search and formatted response generation."""

    def __init__(self, rag: Optional[Any] = None, archetype_mgr: Optional[Any] = None) -> None:
        self.rag = rag
        self.archetype_mgr = archetype_mgr

    def try_resolve_factual(self, prompt: str, context_id: str = "generic") -> Optional[str]:
        """Attempt immediate factual answer from local RAG or archetype entity tables."""
        if not self._is_stat_query(prompt):
            return None

        keywords = self._extract_keywords(prompt)
        entry, data = self._search_knowledge(prompt, context_id, keywords)
        if not entry:
            return None

        return self._format_response(entry, data)

    def _is_stat_query(self, prompt: str) -> bool:
        p = (prompt or "").lower().strip()
        return any(trig in p for trig in STAT_TRIGGERS)

    def _extract_keywords(self, prompt: str) -> List[str]:
        return [
            w.lower()
            for w in re.findall(r"[A-Za-z0-9_\-\.]+", prompt)
            if len(w) > 1 and w.lower() not in STOPWORDS
        ]

    def _search_knowledge(
        self, prompt: str, context_id: str, keywords: List[str]
    ) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        gid = context_id or "generic"

        # Search in RAG repository
        if self.rag and hasattr(self.rag, "search"):
            results = self.rag.search(prompt, game=gid, limit=2)
            for r in results:
                if self._entry_matches(r, keywords):
                    d = self._extract_data(r)
                    if ("penetration" in d and "damage" in d) or "approx_value" in d:
                        return r, d

        # Search in Archetype entity registry
        if self.archetype_mgr and hasattr(self.archetype_mgr, "search_entities"):
            v2_results = self.archetype_mgr.search_entities(prompt, context_id=gid, limit=2)
            for r in v2_results:
                if self._entry_matches(r, keywords):
                    d = self._extract_data(r)
                    if ("penetration" in d and "damage" in d) or "approx_value" in d:
                        return r, d

        return None, {}

    def _entry_matches(self, entry: Dict[str, Any], keywords: List[str]) -> bool:
        if not keywords:
            return True
        haystack = f"{entry.get('title', '')} {entry.get('entity_key', '')}".lower()
        return any(kw in haystack for kw in keywords)

    def _extract_data(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        for field in ("data_json", "facets_json"):
            if entry.get(field):
                try:
                    return json.loads(entry[field])
                except Exception:
                    pass
        if isinstance(entry.get("facets"), dict):
            return entry["facets"]
        return {}

    def _format_response(self, item: Dict[str, Any], data: Dict[str, Any]) -> str:
        title = item.get("title", "Objeto")
        if "penetration" in data and "damage" in data:
            tier_str = f", nivel Tier {data.get('tier', '?')}" if "tier" in data else ""
            return f"La {title} tiene {data['penetration']} de penetración y {data['damage']} de daño base{tier_str}."
        if "approx_value" in data:
            return f"El {title} tiene un valor estimado de mercado de {data['approx_value']:,} Koens."
        return item.get("summary", "")
