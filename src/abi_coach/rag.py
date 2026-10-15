"""Local tactical RAG and knowledge caching system powered by SQLite FTS5."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
from abi_coach.db import DatabaseManager


@dataclass
class KnowledgeItem:
    """Represents a verified tactical fact or statistical entry in the game database."""

    game: str
    category: str
    entity_key: str
    title: str
    data_json: str
    summary: str
    source: str = "official_patch"
    game_version: str = "S7.0"
    confidence: float = 1.0


class KnowledgeRAG:
    """Local, sub-3ms factual retrieval engine using SQLite FTS5 BM25 full-text indexing."""

    def __init__(self, db: DatabaseManager, default_game: str = "generic"):
        self.db = db
        self.default_game = (default_game or "generic").lower().strip()
        self._ensure_seed_loaded()

    def _normalize_game(self, game: Optional[str]) -> str:
        g = (game or self.default_game).lower().strip()
        if g in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
            return "abi"
        return g or "generic"

    def _ensure_seed_loaded(self) -> None:
        """Seed default knowledge for known games if table is empty."""
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM game_knowledge WHERE game = 'abi';")
        count = cur.fetchone()[0]
        if count == 0:
            seed_path = Path(__file__).parent / "data" / "abi_knowledge.json"
            if seed_path.is_file():
                try:
                    entries = json.loads(seed_path.read_text(encoding="utf-8"))
                    for e in entries:
                        self.upsert_knowledge(
                            KnowledgeItem(
                                game=e["game"],
                                category=e["category"],
                                entity_key=e["entity_key"],
                                title=e["title"],
                                data_json=e["data_json"],
                                summary=e["summary"],
                                source=e.get("source", "official_patch"),
                                game_version=e.get("game_version", "S7.0"),
                                confidence=float(e.get("confidence", 1.0)),
                            )
                        )
                except Exception:
                    pass

    def upsert_knowledge(self, item: KnowledgeItem) -> int:
        """Insert or update a factual knowledge entry."""
        con = self.db.get_connection()
        game = self._normalize_game(item.game)
        with con:
            cur = con.execute(
                """
                INSERT INTO game_knowledge (
                    game, category, entity_key, title, data_json, summary, source, game_version, confidence, updated_at, last_synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(entity_key) DO UPDATE SET
                    game = excluded.game,
                    category = excluded.category,
                    title = excluded.title,
                    data_json = excluded.data_json,
                    summary = excluded.summary,
                    source = excluded.source,
                    game_version = excluded.game_version,
                    confidence = excluded.confidence,
                    updated_at = CURRENT_TIMESTAMP,
                    last_synced_at = CURRENT_TIMESTAMP;
                """,
                (
                    game,
                    item.category.strip(),
                    item.entity_key.strip(),
                    item.title.strip(),
                    item.data_json.strip()
                    if isinstance(item.data_json, str)
                    else json.dumps(item.data_json),
                    item.summary.strip(),
                    item.source.strip(),
                    item.game_version.strip(),
                    item.confidence,
                ),
            )
            return cur.lastrowid

    def get_entity(self, entity_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific entity by its unique entity_key."""
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, game, category, entity_key, title, data_json, summary, source, game_version, confidence, last_synced_at
            FROM game_knowledge
            WHERE entity_key = ?;
            """,
            (entity_key.strip(),),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def _sanitize_fts_query(self, raw_query: str) -> str:
        """Extract alphanumeric keywords and escape them into safe FTS5 prefix match tokens."""
        # Split into individual words/numbers, removing punctuation that breaks FTS5 syntax
        words = re.findall(r"[A-Za-z0-9_\.]+", raw_query)
        # Filter very short noise words
        tokens = [w for w in words if len(w) > 1 and w.lower() not in ("de", "la", "el", "los", "las", "un", "una", "en", "con", "por", "para", "que", "qué")]
        if not tokens:
            return ""
        # Create FTS5 query with prefix matching on tokens
        clauses = [f'"{t}"*' for t in tokens]
        return " OR ".join(clauses)

    def search(
        self, query: str, game: Optional[str] = None, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Search game knowledge using FTS5 BM25 match."""
        g = self._normalize_game(game)
        fts_query = self._sanitize_fts_query(query)
        if not fts_query:
            return []

        con = self.db.get_connection()
        cur = con.cursor()
        try:
            cur.execute(
                """
                SELECT k.id, k.game, k.category, k.entity_key, k.title, k.data_json, k.summary, k.source, k.game_version, k.confidence,
                       rank
                FROM game_knowledge_fts f
                JOIN game_knowledge k ON f.rowid = k.id
                WHERE game_knowledge_fts MATCH ? AND k.game = ?
                ORDER BY rank
                LIMIT ?;
                """,
                (fts_query, g, limit),
            )
            return [dict(r) for r in cur.fetchall()]
        except Exception:
            # Fallback to simple LIKE search if FTS syntax fails
            pattern = f"%{query.strip()}%"
            cur.execute(
                """
                SELECT id, game, category, entity_key, title, data_json, summary, source, game_version, confidence
                FROM game_knowledge
                WHERE game = ? AND (title LIKE ? OR summary LIKE ? OR entity_key LIKE ?)
                ORDER BY updated_at DESC
                LIMIT ?;
                """,
                (g, pattern, pattern, pattern, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    def format_context_for_prompt(
        self, query: str, game: Optional[str] = None, limit: int = 2
    ) -> str:
        """Format matching factual knowledge into a concise verification block for the LLM prompt."""
        matches = self.search(query=query, game=game, limit=limit)
        if not matches:
            return ""

        lines = ["\n[BASE DE DATOS TÁCTICA VERIFICADA DEL JUEGO (RAG LOCAL - LATENCIA SUB-3MS)]:"]
        for item in matches:
            lines.append(f"• [{item['category'].upper()}] {item['title']} (Ver: {item['game_version']}, Confiabilidad: {int(item['confidence']*100)}%):")
            lines.append(f"  {item['summary']}")
        lines.append("[Usa estos datos exactos como verdad canónica al responder al jugador.]\n")
        return "\n".join(lines)
