"""Knowledge reconciler and self-healing engine for detecting patch and vision incongruities (Tactical RAG Slice)."""

from dataclasses import dataclass
import json
from typing import Any, Dict, List, Optional
from abi_coach.core.storage.db import DatabaseManager
from abi_coach.slices.tactical_rag.rag import KnowledgeItem, KnowledgeRAG


@dataclass
class ReconciliationDiff:
    """Represents a discrepancy between existing cached knowledge and new observation."""

    entity_key: str
    field_name: str
    old_value: Any
    new_value: Any
    reason: str


class KnowledgeReconciler:
    """Detects discrepancies between ground-truth observations and cached RAG facts, updating knowledge with an audit trail."""

    def __init__(self, db: DatabaseManager, rag: KnowledgeRAG):
        self.db = db
        self.rag = rag

    def reconcile_entity(
        self,
        entity_key: str,
        observed_data: Dict[str, Any],
        title: Optional[str] = None,
        category: Optional[str] = None,
        game: Optional[str] = None,
        reason: str = "vision_observed",
        confidence: float = 0.95,
        new_summary: Optional[str] = None,
    ) -> List[ReconciliationDiff]:
        """Compare observed attributes against stored entity, update SQLite, and log diffs in changelog."""
        con = self.db.get_connection()
        existing = self.rag.get_entity(entity_key)
        diffs: List[ReconciliationDiff] = []

        if existing is None:
            # Brand new entity discovered
            g = (game or self.rag.default_game).lower()
            cat = category or "general"
            tit = title or entity_key
            summary = new_summary or f"Información descubierta sobre {tit}."

            item = KnowledgeItem(
                game=g,
                category=cat,
                entity_key=entity_key,
                title=tit,
                data_json=json.dumps(observed_data, ensure_ascii=False),
                summary=summary,
                source=reason,
                confidence=confidence,
            )
            self.rag.upsert_knowledge(item)

            with con:
                con.execute(
                    """
                    INSERT INTO knowledge_changelog (entity_key, field_name, old_value, new_value, reason)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (entity_key, "entity_creation", None, json.dumps(observed_data), reason),
                )
            diffs.append(
                ReconciliationDiff(
                    entity_key=entity_key,
                    field_name="entity_creation",
                    old_value=None,
                    new_value=observed_data,
                    reason=reason,
                )
            )
            return diffs

        # Existing entity: parse stored JSON
        current_data = {}
        try:
            current_data = json.loads(existing["data_json"])
        except Exception:
            pass

        # Detect field differences
        updated_data = dict(current_data)
        for k, new_v in observed_data.items():
            old_v = current_data.get(k)
            # Compare primitive or string representation
            if old_v != new_v:
                diffs.append(
                    ReconciliationDiff(
                        entity_key=entity_key,
                        field_name=k,
                        old_value=old_v,
                        new_value=new_v,
                        reason=reason,
                    )
                )
                updated_data[k] = new_v

        if not diffs:
            return []

        # Log diffs to knowledge_changelog
        with con:
            for diff in diffs:
                con.execute(
                    """
                    INSERT INTO knowledge_changelog (entity_key, field_name, old_value, new_value, reason)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        entity_key,
                        diff.field_name,
                        str(diff.old_value) if diff.old_value is not None else None,
                        str(diff.new_value),
                        reason,
                    ),
                )

        # Update stored knowledge record
        summary = new_summary or existing["summary"]
        updated_item = KnowledgeItem(
            game=existing["game"],
            category=existing["category"],
            entity_key=entity_key,
            title=title or existing["title"],
            data_json=json.dumps(updated_data, ensure_ascii=False),
            summary=summary,
            source=reason,
            game_version=existing.get("game_version", "S7.0"),
            confidence=confidence,
        )
        self.rag.upsert_knowledge(updated_item)
        return diffs

    def get_changelog(
        self, entity_key: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve recent reconciliation changelog history."""
        con = self.db.get_connection()
        cur = con.cursor()
        if entity_key:
            cur.execute(
                """
                SELECT id, entity_key, field_name, old_value, new_value, reason, timestamp
                FROM knowledge_changelog
                WHERE entity_key = ?
                ORDER BY timestamp DESC
                LIMIT ?;
                """,
                (entity_key, limit),
            )
        else:
            cur.execute(
                """
                SELECT id, entity_key, field_name, old_value, new_value, reason, timestamp
                FROM knowledge_changelog
                ORDER BY timestamp DESC
                LIMIT ?;
                """,
                (limit,),
            )
        return [dict(r) for r in cur.fetchall()]

    def format_reconciliation_notice(self, diffs: List[ReconciliationDiff]) -> str:
        """Create a concise voice/prompt alert describing detected stat discrepancies."""
        if not diffs:
            return ""

        parts = []
        for d in diffs:
            if d.field_name == "entity_creation":
                parts.append(f"Se indexó nueva entidad {d.entity_key}.")
            else:
                parts.append(f"{d.field_name} cambió de {d.old_value} a {d.new_value}")
        return f"[ACTUALIZACIÓN DE PARCHE / DATOS RECONCILIADOS]: {', '.join(parts)}."
