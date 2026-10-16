"""Autonomous scaffolding and replication engine for zero-seeder topic onboarding (Archetypes Slice)."""

from dataclasses import dataclass
import json
import re
from typing import Any, Dict, List, Optional
from abi_coach.application.slices.archetypes.manager import (
    ArchetypeManager,
    DynamicEntity,
    EngramObservation,
    TopicContext,
)
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager


class ArchetypeScaffolder:
    """Provisions and replicates new game topics from archetype blueprints without manual seeders."""

    def __init__(self, db: DatabaseManager, archetype_mgr: Optional[ArchetypeManager] = None):
        self.db = db
        self.mgr = archetype_mgr if archetype_mgr is not None else ArchetypeManager(db)

    def detect_archetype(self, game_name: str, hint_text: Optional[str] = None) -> str:
        """Infer best matching domain archetype from game name or description keywords."""
        combined = f"{game_name} {hint_text or ''}".lower()
        words = set(re.findall(r"[a-z0-9]+", combined))

        # 1. RPG & MMO signals
        rpg_terms = {"rpg", "elden", "warcraft", "diablo", "souls", "mmo", "dungeon", "affix", "talent", "leveling", "mana"}
        if words & rpg_terms:
            return "rpg_mmo"

        # 2. Extraction shooter signals
        extraction_terms = {"extraction", "breakout", "tarkov", "hunt", "arena", "raid", "koen"}
        if (words & extraction_terms) or "loot & escape" in combined:
            return "extraction_shooter"

        # 3. Survival crafting signals
        survival_terms = {"survival", "rust", "ark", "craft", "palworld", "silo", "calibrations", "base"}
        if (words & survival_terms) or "once human" in combined:
            return "survival_craft"

        # Default fallback
        return "general_companion"

    def bootstrap_context(
        self,
        context_id: str,
        archetype_id: Optional[str] = None,
        display_name: Optional[str] = None,
        initial_config: Optional[Dict[str, Any]] = None,
        activate: bool = True,
    ) -> TopicContext:
        """Dynamically provision a new game topic context, seeding archetype rules and observations."""
        cid = context_id.strip().lower()
        dname = display_name or context_id.replace("_", " ").title()

        arch_id = archetype_id or self.detect_archetype(cid, dname)
        archetype = self.mgr.get_archetype(arch_id)
        if archetype is None:
            arch_id = "general_companion"
            archetype = self.mgr.get_archetype("general_companion")

        cfg = dict(initial_config or {})
        if "archetype_template" not in cfg and archetype:
            cfg["archetype_template"] = archetype.schema_template

        # 1. Register topic context in database
        context = self.mgr.create_context(
            context_id=cid,
            archetype_id=arch_id,
            display_name=dname,
            config=cfg,
            activate=activate,
        )

        # 2. Scaffolding default foundational Engram observations
        base_observations = [
            EngramObservation(
                context_id=cid,
                scope="project",
                topic_key=f"{cid}/player/profile",
                observation_type="preference",
                title=f"Perfil del Jugador en {dname}",
                content=f"**What**: Registro de preferencias, estilo de juego y progreso en {dname}.\n**Why**: Personalizar asistencia táctica.\n**Where**: Contexto activo de juego.",
                pinned=True,
            ),
            EngramObservation(
                context_id=cid,
                scope="project",
                topic_key=f"{cid}/rules/tactical",
                observation_type="rule",
                title=f"Reglas Tácticas Fundamentales - {dname}",
                content=f"**What**: {archetype.default_system_prompt if archetype else 'Asistencia ágil y breve.'}\n**Why**: Mantener respuestas concisas sin saturar audio.\n**Where**: Sistema de síntesis de voz.",
                pinned=True,
            ),
        ]

        for obs in base_observations:
            self.mgr.save_engram_observation(obs)

        return context

    def auto_ingest_fact(
        self,
        context_id: str,
        category: str,
        title: str,
        summary: str,
        facets: Optional[Dict[str, Any]] = None,
        source: str = "vision_discovered",
        confidence: float = 0.95,
    ) -> DynamicEntity:
        """Ingest a freshly discovered game entity dynamically without requiring static seed files."""
        cid = context_id.strip().lower()
        # Ensure context exists
        if not self.mgr.get_context(cid):
            self.bootstrap_context(cid)

        # Build clean alphanumeric key
        ascii_title = "".join(c if c.isalnum() else "_" for c in title.lower())
        safe_key = f"{category.strip().lower()}:{cid}:{ascii_title[:30].strip('_')}"

        entity = DynamicEntity(
            context_id=cid,
            category=category.strip().lower(),
            entity_key=safe_key,
            title=title.strip(),
            facets=facets or {},
            summary=summary.strip(),
            confidence=confidence,
            source=source,
        )
        self.mgr.upsert_entity(entity)
        return entity
