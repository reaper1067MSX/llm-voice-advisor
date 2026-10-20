"""SQLite repository adapter for dynamic archetypes, contexts, entities, and Engram observations."""

import json
import re
import sqlite3
from typing import Any, Optional

from abi_coach.domain.entities.archetype_entities import (
    SPANISH_FTS_STOPWORDS,
    ArchetypeDefinition,
    DynamicEntity,
    EngramObservation,
    TopicContext,
)
from abi_coach.infrastructure.adapters.storage.db import DatabaseManager


def sanitize_fts_query(raw_query: str) -> str:
    """Sanitize user query into an FTS5 prefix OR clause excluding Spanish stopwords."""
    words = re.findall(r"[A-Za-z0-9_\.]+", raw_query)
    tokens = [w for w in words if len(w) > 1 and w.lower() not in SPANISH_FTS_STOPWORDS]
    return " OR ".join(f'"{t}"*' for t in tokens) if tokens else ""


def _parse_json_dict(raw_json: Any) -> dict[str, Any]:
    if not raw_json:
        return {}
    try:
        parsed = json.loads(raw_json)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _row_to_entity_dict(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["facets"] = _parse_json_dict(item.get("facets_json"))
    return item


def _row_to_archetype(row: Any) -> ArchetypeDefinition:
    tmpl = _parse_json_dict(row["schema_template"])
    return ArchetypeDefinition(
        row["archetype_id"], row["display_name"], tmpl, row["default_system_prompt"]
    )


class SqliteArchetypeRepository:
    """SQLite implementation of ArchetypeRepositoryPort over DatabaseManager."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def list_archetypes(self) -> list[ArchetypeDefinition]:
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT archetype_id, display_name, schema_template, default_system_prompt "
            "FROM topic_archetypes;"
        )
        return [_row_to_archetype(r) for r in cur.fetchall()]

    def get_archetype(self, archetype_id: str) -> Optional[ArchetypeDefinition]:
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT archetype_id, display_name, schema_template, default_system_prompt "
            "FROM topic_archetypes WHERE archetype_id = ?;",
            (archetype_id.strip().lower(),),
        )
        row = cur.fetchone()
        return _row_to_archetype(row) if row else None

    def create_context(
        self,
        context_id: str,
        archetype_id: str,
        display_name: str,
        config: Optional[dict[str, Any]] = None,
        version: str = "1.0",
        activate: bool = True,
    ) -> TopicContext:
        con = self.db.get_connection()
        cid = context_id.strip().lower()
        cfg_json = json.dumps(config or {})
        with con:
            if activate:
                con.execute("UPDATE topic_contexts SET is_active = 0;")
            con.execute(
                "INSERT INTO topic_contexts (context_id, archetype_id, display_name, "
                "current_version, config_json, is_active, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(context_id) DO UPDATE SET archetype_id = excluded.archetype_id, "
                "display_name = excluded.display_name, current_version = excluded.current_version, "
                "config_json = excluded.config_json, is_active = excluded.is_active, "
                "updated_at = CURRENT_TIMESTAMP;",
                (cid, archetype_id, display_name, version, cfg_json, 1 if activate else 0),
            )
        return TopicContext(cid, archetype_id, display_name, version, config or {}, activate)

    def get_context(self, context_id: str) -> Optional[TopicContext]:
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT context_id, archetype_id, display_name, current_version, "
            "config_json, is_active FROM topic_contexts WHERE context_id = ?;",
            (context_id.strip().lower(),),
        )
        r = cur.fetchone()
        if not r:
            return None
        cfg, active = _parse_json_dict(r["config_json"]), bool(r["is_active"])
        return TopicContext(
            r["context_id"], r["archetype_id"], r["display_name"], r["current_version"], cfg, active
        )

    def upsert_entity(self, entity: DynamicEntity) -> int:
        con = self.db.get_connection()
        facets_str = (
            json.dumps(entity.facets, ensure_ascii=False)
            if isinstance(entity.facets, dict)
            else str(entity.facets)
        )
        params = (
            entity.context_id.strip().lower(),
            entity.category.strip(),
            entity.entity_key.strip(),
            entity.title.strip(),
            facets_str,
            entity.summary.strip(),
            entity.confidence,
            entity.source.strip(),
        )
        with con:
            cur = con.execute(
                "INSERT INTO topic_entities (context_id, category, entity_key, title, "
                "facets_json, summary, confidence, source, updated_at, last_synced_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                "ON CONFLICT(entity_key) DO UPDATE SET context_id = excluded.context_id, "
                "category = excluded.category, title = excluded.title, "
                "facets_json = excluded.facets_json, summary = excluded.summary, "
                "confidence = excluded.confidence, source = excluded.source, "
                "updated_at = CURRENT_TIMESTAMP, last_synced_at = CURRENT_TIMESTAMP;",
                params,
            )
            return int(cur.lastrowid or 0)

    def get_entity(self, entity_key: str) -> Optional[dict[str, Any]]:
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT id, context_id, category, entity_key, title, facets_json, "
            "summary, confidence, source, last_synced_at FROM topic_entities WHERE entity_key = ?;",
            (entity_key.strip(),),
        )
        row = cur.fetchone()
        return _row_to_entity_dict(row) if row else None

    def search_entities(self, query: str, context_id: str, limit: int = 5) -> list[dict[str, Any]]:
        fts_query = sanitize_fts_query(query)
        if not fts_query:
            return []
        cur = self.db.get_connection().cursor()
        cid = context_id.strip().lower()
        try:
            cur.execute(
                "SELECT e.id, e.context_id, e.category, e.entity_key, e.title, e.facets_json, "
                "e.summary, e.confidence, e.source, rank FROM topic_entities_fts f "
                "JOIN topic_entities e ON f.rowid = e.id "
                "WHERE topic_entities_fts MATCH ? AND e.context_id = ? ORDER BY rank LIMIT ?;",
                (fts_query, cid, limit),
            )
            return [_row_to_entity_dict(row) for row in cur.fetchall()]
        except sqlite3.Error:
            pat = f"%{query}%"
            cur.execute(
                "SELECT id, context_id, category, entity_key, title, facets_json, summary, "
                "confidence, source FROM topic_entities WHERE context_id = ? "
                "AND (title LIKE ? OR summary LIKE ? OR entity_key LIKE ?) "
                "ORDER BY updated_at DESC LIMIT ?;",
                (cid, pat, pat, pat, limit),
            )
            return [_row_to_entity_dict(row) for row in cur.fetchall()]

    def save_engram_observation(self, obs: EngramObservation) -> int:
        con = self.db.get_connection()
        params = (
            obs.context_id.strip().lower(),
            obs.scope,
            obs.topic_key.strip(),
            obs.observation_type.strip(),
            obs.title.strip(),
            obs.content.strip(),
            1 if obs.pinned else 0,
        )
        with con:
            cur = con.execute(
                "INSERT INTO engram_observations (context_id, scope, topic_key, "
                "observation_type, title, content, pinned, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(topic_key) DO UPDATE SET context_id = excluded.context_id, "
                "scope = excluded.scope, observation_type = excluded.observation_type, "
                "title = excluded.title, content = excluded.content, "
                "pinned = excluded.pinned, updated_at = CURRENT_TIMESTAMP;",
                params,
            )
            return int(cur.lastrowid or 0)

    def get_engram_observations(self, context_id: str, limit: int = 6) -> list[dict[str, Any]]:
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT id, context_id, scope, topic_key, observation_type, title, content, "
            "pinned, access_count, updated_at FROM engram_observations WHERE context_id = ? "
            "ORDER BY pinned DESC, updated_at DESC LIMIT ?;",
            (context_id.strip().lower(), limit),
        )
        return [dict(row) for row in cur.fetchall()]


__all__ = ["SqliteArchetypeRepository", "sanitize_fts_query"]
