"""Dynamic Archetype-based Topic & Entity Manager following gentle-ai / Engram standards (Archetypes Slice)."""

from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager


@dataclass
class ArchetypeDefinition:
    """Foundational domain archetype blueprint for a family of games or topics."""

    archetype_id: str
    display_name: str
    schema_template: Dict[str, Any]
    default_system_prompt: str


@dataclass
class TopicContext:
    """An instantiated topic domain / game context linked to an archetype."""

    context_id: str
    archetype_id: str
    display_name: str
    current_version: str = "1.0"
    config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = False


@dataclass
class DynamicEntity:
    """Entity with dynamic facet attributes (no rigid ballistic columns)."""

    context_id: str
    category: str
    entity_key: str
    title: str
    facets: Dict[str, Any]
    summary: str
    confidence: float = 1.0
    source: str = "system"


@dataclass
class EngramObservation:
    """Engram-compliant observation representing learned player patterns and rules."""

    context_id: str
    scope: str  # 'project' or 'personal'
    topic_key: str  # e.g., 'loadouts/primary', 'rules/engagement'
    observation_type: str  # 'preference', 'discovery', 'rule', 'config', 'decision'
    title: str
    content: str  # Structured content (**What**, **Why**, **Where**, **Learned**)
    pinned: bool = False
    access_count: int = 0


class ArchetypeManager:
    """Manages archetype blueprints, topic contexts, dynamic entities, and Engram observations."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def list_archetypes(self) -> List[ArchetypeDefinition]:
        """List all available foundational domain archetypes."""
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute("SELECT archetype_id, display_name, schema_template, default_system_prompt FROM topic_archetypes;")
        result = []
        for r in cur.fetchall():
            tmpl = {}
            try:
                tmpl = json.loads(r["schema_template"])
            except Exception:
                pass
            result.append(
                ArchetypeDefinition(
                    archetype_id=r["archetype_id"],
                    display_name=r["display_name"],
                    schema_template=tmpl,
                    default_system_prompt=r["default_system_prompt"],
                )
            )
        return result

    def get_archetype(self, archetype_id: str) -> Optional[ArchetypeDefinition]:
        """Retrieve an archetype by its unique ID."""
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT archetype_id, display_name, schema_template, default_system_prompt FROM topic_archetypes WHERE archetype_id = ?;",
            (archetype_id.strip().lower(),),
        )
        r = cur.fetchone()
        if r:
            tmpl = {}
            try:
                tmpl = json.loads(r["schema_template"])
            except Exception:
                pass
            return ArchetypeDefinition(
                archetype_id=r["archetype_id"],
                display_name=r["display_name"],
                schema_template=tmpl,
                default_system_prompt=r["default_system_prompt"],
            )
        return None

    def create_context(
        self,
        context_id: str,
        archetype_id: str,
        display_name: str,
        config: Optional[Dict[str, Any]] = None,
        version: str = "1.0",
        activate: bool = True,
    ) -> TopicContext:
        """Create or update a topic context linked to an archetype blueprint."""
        con = self.db.get_connection()
        cid = context_id.strip().lower()
        cfg_json = json.dumps(config or {})

        with con:
            if activate:
                con.execute("UPDATE topic_contexts SET is_active = 0;")

            con.execute(
                """
                INSERT INTO topic_contexts (context_id, archetype_id, display_name, current_version, config_json, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(context_id) DO UPDATE SET
                    archetype_id = excluded.archetype_id,
                    display_name = excluded.display_name,
                    current_version = excluded.current_version,
                    config_json = excluded.config_json,
                    is_active = excluded.is_active,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (cid, archetype_id, display_name, version, cfg_json, 1 if activate else 0),
            )

        return TopicContext(
            context_id=cid,
            archetype_id=archetype_id,
            display_name=display_name,
            current_version=version,
            config=config or {},
            is_active=activate,
        )

    def get_context(self, context_id: str) -> Optional[TopicContext]:
        """Retrieve an active or registered topic context by ID."""
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT context_id, archetype_id, display_name, current_version, config_json, is_active FROM topic_contexts WHERE context_id = ?;",
            (context_id.strip().lower(),),
        )
        r = cur.fetchone()
        if r:
            cfg = {}
            try:
                cfg = json.loads(r["config_json"])
            except Exception:
                pass
            return TopicContext(
                context_id=r["context_id"],
                archetype_id=r["archetype_id"],
                display_name=r["display_name"],
                current_version=r["current_version"],
                config=cfg,
                is_active=bool(r["is_active"]),
            )
        return None

    def upsert_entity(self, entity: DynamicEntity) -> int:
        """Upsert a dynamic entity with JSON facets and FTS5 indexing."""
        con = self.db.get_connection()
        facets_str = json.dumps(entity.facets, ensure_ascii=False) if isinstance(entity.facets, dict) else str(entity.facets)

        with con:
            cur = con.execute(
                """
                INSERT INTO topic_entities (
                    context_id, category, entity_key, title, facets_json, summary, confidence, source, updated_at, last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(entity_key) DO UPDATE SET
                    context_id = excluded.context_id,
                    category = excluded.category,
                    title = excluded.title,
                    facets_json = excluded.facets_json,
                    summary = excluded.summary,
                    confidence = excluded.confidence,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP,
                    last_synced_at = CURRENT_TIMESTAMP;
                """,
                (
                    entity.context_id.strip().lower(),
                    entity.category.strip(),
                    entity.entity_key.strip(),
                    entity.title.strip(),
                    facets_str,
                    entity.summary.strip(),
                    entity.confidence,
                    entity.source.strip(),
                ),
            )
            return cur.lastrowid

    def get_entity(self, entity_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve an entity by unique entity_key."""
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, context_id, category, entity_key, title, facets_json, summary, confidence, source, last_synced_at
            FROM topic_entities WHERE entity_key = ?;
            """,
            (entity_key.strip(),),
        )
        r = cur.fetchone()
        if r:
            d = dict(r)
            try:
                d["facets"] = json.loads(d["facets_json"])
            except Exception:
                d["facets"] = {}
            return d
        return None

    def _sanitize_fts_query(self, raw_query: str) -> str:
        words = re.findall(r"[A-Za-z0-9_\.]+", raw_query)
        tokens = [w for w in words if len(w) > 1 and w.lower() not in ("de", "la", "el", "los", "las", "un", "una", "en", "con", "por", "para", "que", "qué")]
        if not tokens:
            return ""
        clauses = [f'"{t}"*' for t in tokens]
        return " OR ".join(clauses)

    def search_entities(
        self, query: str, context_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform sub-2ms FTS5 BM25 search over dynamic entities within context."""
        fts_query = self._sanitize_fts_query(query)
        if not fts_query:
            return []

        con = self.db.get_connection()
        cur = con.cursor()
        cid = context_id.strip().lower()

        try:
            cur.execute(
                """
                SELECT e.id, e.context_id, e.category, e.entity_key, e.title, e.facets_json, e.summary, e.confidence, e.source,
                       rank
                FROM topic_entities_fts f
                JOIN topic_entities e ON f.rowid = e.id
                WHERE topic_entities_fts MATCH ? AND e.context_id = ?
                ORDER BY rank
                LIMIT ?;
                """,
                (fts_query, cid, limit),
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["facets"] = json.loads(item["facets_json"])
                except Exception:
                    item["facets"] = {}
                results.append(item)
            return results
        except Exception:
            # Fallback to LIKE query
            cur.execute(
                """
                SELECT id, context_id, category, entity_key, title, facets_json, summary, confidence, source
                FROM topic_entities
                WHERE context_id = ? AND (title LIKE ? OR summary LIKE ? OR entity_key LIKE ?)
                ORDER BY updated_at DESC LIMIT ?;
                """,
                (cid, f"%{query}%", f"%{query}%", f"%{query}%", limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def save_engram_observation(self, obs: EngramObservation) -> int:
        """Save observation conforming 100% to gentle-ai Engram specification."""
        con = self.db.get_connection()
        cid = obs.context_id.strip().lower()

        with con:
            cur = con.execute(
                """
                INSERT INTO engram_observations (
                    context_id, scope, topic_key, observation_type, title, content, pinned, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(topic_key) DO UPDATE SET
                    context_id = excluded.context_id,
                    scope = excluded.scope,
                    observation_type = excluded.observation_type,
                    title = excluded.title,
                    content = excluded.content,
                    pinned = excluded.pinned,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (
                    cid,
                    obs.scope,
                    obs.topic_key.strip(),
                    obs.observation_type.strip(),
                    obs.title.strip(),
                    obs.content.strip(),
                    1 if obs.pinned else 0,
                ),
            )
            return cur.lastrowid

    def get_engram_observations(
        self, context_id: str, limit: int = 6
    ) -> List[Dict[str, Any]]:
        """Retrieve top active observations for prompt enrichment."""
        cid = context_id.strip().lower()
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, context_id, scope, topic_key, observation_type, title, content, pinned, access_count, updated_at
            FROM engram_observations
            WHERE context_id = ?
            ORDER BY pinned DESC, updated_at DESC
            LIMIT ?;
            """,
            (cid, limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def format_profile_for_prompt(self, context_id: str, limit: int = 6) -> str:
        """Format active Engram observations into a prompt injection block."""
        obs = self.get_engram_observations(context_id=context_id, limit=limit)
        if not obs:
            return ""

        lines = [f"\n[MEMORIA PERSISTENTE ENGRAM - CONTEXTO: {context_id.upper()}]:"]
        for o in obs:
            pin = "⭐ " if o.get("pinned") else "- "
            lines.append(f"{pin}[{o['observation_type'].upper()}] {o['title']}: {o['content']}")
        lines.append("[FIN DE MEMORIA ENGRAM: Personaliza tus respuestas según estas pautas.]\n")
        return "\n".join(lines)

    def format_rag_for_prompt(
        self, query: str, context_id: str, limit: int = 2
    ) -> str:
        """Format matching dynamic entities (v2 topic_entities) into a verification block for the LLM prompt."""
        matches = self.search_entities(query=query, context_id=context_id, limit=limit)
        if not matches:
            return ""

        lines = [f"\n[ENTIDADES DINÁMICAS DEL CONTEXTO ({context_id.upper()})]:"]
        for item in matches:
            conf_pct = int(float(item.get("confidence", 1.0)) * 100)
            lines.append(
                f"• [{item['category'].upper()}] {item['title']} (Confiabilidad: {conf_pct}%):"
            )
            lines.append(f"  {item['summary']}")
            facets = item.get("facets")
            if not facets and item.get("facets_json"):
                try:
                    facets = json.loads(item["facets_json"])
                except Exception:
                    facets = {}
            if facets:
                lines.append(f"  Atributos: {json.dumps(facets, ensure_ascii=False)}")
        lines.append("[Usa estos datos exactos como verdad canónica al responder al jugador.]\n")
        return "\n".join(lines)

