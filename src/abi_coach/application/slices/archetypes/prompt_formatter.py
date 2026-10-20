"""Prompt formatting helpers for Archetypes Engram profiles and dynamic entity RAG."""

import json
from typing import Any


class ArchetypePromptFormatter:
    """Formats Engram observations and dynamic entities into LLM prompt blocks."""

    def format_profile_for_prompt(
        self,
        context_id: str,
        observations: list[dict[str, Any]],
    ) -> str:
        """Format active Engram observations into a prompt injection block."""
        if not observations:
            return ""

        lines = [f"\n[MEMORIA PERSISTENTE ENGRAM - CONTEXTO: {context_id.upper()}]:"]
        for obs in observations:
            pin = "⭐ " if obs.get("pinned") else "- "
            obs_type = str(obs.get("observation_type", "")).upper()
            lines.append(f"{pin}[{obs_type}] {obs['title']}: {obs['content']}")
        lines.append("[FIN DE MEMORIA ENGRAM: Personaliza tus respuestas según estas pautas.]\n")
        return "\n".join(lines)

    def format_rag_for_prompt(
        self,
        context_id: str,
        matches: list[dict[str, Any]],
    ) -> str:
        """Format matching dynamic entities into a verification block for the LLM prompt."""
        if not matches:
            return ""

        lines = [f"\n[ENTIDADES DINÁMICAS DEL CONTEXTO ({context_id.upper()})]:"]
        for item in matches:
            conf_pct = int(float(item.get("confidence", 1.0)) * 100)
            category = str(item.get("category", "")).upper()
            lines.append(f"• [{category}] {item['title']} (Confiabilidad: {conf_pct}%):")
            lines.append(f"  {item['summary']}")
            facets = item.get("facets")
            if not facets and item.get("facets_json"):
                try:
                    facets = json.loads(item["facets_json"])
                except (json.JSONDecodeError, TypeError, ValueError):
                    facets = {}
            if facets:
                lines.append(f"  Atributos: {json.dumps(facets, ensure_ascii=False)}")
        lines.append("[Usa estos datos exactos como verdad canónica al responder al jugador.]\n")
        return "\n".join(lines)


__all__ = ["ArchetypePromptFormatter"]
