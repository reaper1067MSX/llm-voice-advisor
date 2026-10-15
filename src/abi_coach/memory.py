"""Hierarchical persistent companion memory system (game -> topic -> feature)."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from abi_coach.db import DatabaseManager


@dataclass
class MemoryItem:
    """Represents a discrete memory observation or preference in the companion brain."""

    game: str
    topic: str
    feature: str
    topic_key: str
    memory_type: str  # 'preference', 'discovery', 'decision', 'stat', 'event'
    title: str
    content: str
    pinned: bool = False


class CompanionMemory:
    """Provides storage, retrieval, and prompt formatting of player memories across sessions."""

    def __init__(self, db: DatabaseManager, default_game: str = "generic"):
        self.db = db
        self.default_game = (default_game or "generic").lower().strip()

    def _normalize_game(self, game: Optional[str]) -> str:
        g = (game or self.default_game).lower().strip()
        if g in ("abi", "arena_breakout", "arena_breakout_infinite", "arena-breakout"):
            return "abi"
        return g or "generic"

    def save_memory(self, item: MemoryItem) -> int:
        """Upsert a memory entry by topic_key. Returns rowid."""
        con = self.db.get_connection()
        game = self._normalize_game(item.game)
        with con:
            cur = con.execute(
                """
                INSERT INTO companion_memories (
                    game, topic, feature, topic_key, memory_type, title, content, pinned, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(topic_key) DO UPDATE SET
                    game = excluded.game,
                    topic = excluded.topic,
                    feature = excluded.feature,
                    memory_type = excluded.memory_type,
                    title = excluded.title,
                    content = excluded.content,
                    pinned = excluded.pinned,
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (
                    game,
                    item.topic.strip(),
                    item.feature.strip(),
                    item.topic_key.strip(),
                    item.memory_type.strip(),
                    item.title.strip(),
                    item.content.strip(),
                    1 if item.pinned else 0,
                ),
            )
            return cur.lastrowid

    def get_memory(self, topic_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by its unique topic_key."""
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, game, topic, feature, topic_key, memory_type, title, content, pinned, access_count, created_at, updated_at
            FROM companion_memories
            WHERE topic_key = ?;
            """,
            (topic_key.strip(),),
        )
        row = cur.fetchone()
        if row:
            # Increment access count
            data = dict(row)
            data["access_count"] += 1
            with con:
                con.execute(
                    "UPDATE companion_memories SET access_count = ? WHERE id = ?",
                    (data["access_count"], data["id"]),
                )
            return data
        return None

    def get_active_profile(
        self, game: Optional[str] = None, limit: int = 6
    ) -> List[Dict[str, Any]]:
        """Retrieve top active/pinned memories for the given game."""
        g = self._normalize_game(game)
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, game, topic, feature, topic_key, memory_type, title, content, pinned, access_count, updated_at
            FROM companion_memories
            WHERE game = ?
            ORDER BY pinned DESC, updated_at DESC
            LIMIT ?;
            """,
            (g, limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def search_memories(
        self, query: str, game: Optional[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Perform keyword search across titles, contents, and features."""
        g = self._normalize_game(game)
        q = f"%{query.strip()}%"
        con = self.db.get_connection()
        cur = con.cursor()
        cur.execute(
            """
            SELECT id, game, topic, feature, topic_key, memory_type, title, content, pinned, updated_at
            FROM companion_memories
            WHERE game = ? AND (title LIKE ? OR content LIKE ? OR feature LIKE ? OR topic LIKE ?)
            ORDER BY pinned DESC, updated_at DESC
            LIMIT ?;
            """,
            (g, q, q, q, q, limit),
        )
        return [dict(r) for r in cur.fetchall()]

    def delete_memory(self, topic_key: str) -> bool:
        """Delete a memory by its topic_key. Returns True if deleted."""
        con = self.db.get_connection()
        with con:
            cur = con.execute(
                "DELETE FROM companion_memories WHERE topic_key = ?;",
                (topic_key.strip(),),
            )
            return cur.rowcount > 0

    def format_profile_for_prompt(self, game: Optional[str] = None, limit: int = 6) -> str:
        """Format active memories into a compact markdown context block for the system prompt."""
        memories = self.get_active_profile(game=game, limit=limit)
        if not memories:
            return ""

        lines = ["\n[MEMORIA PERSISTENTE DEL JUGADOR - HISTORIAL Y PREFERENCIAS RECORDADAS]:"]
        for m in memories:
            prefix = "⭐ " if m.get("pinned") else "- "
            lines.append(f"{prefix}[{m['topic']}/{m['feature']}] {m['title']}: {m['content']}")
        lines.append(
            "[FIN DE MEMORIA: Usa esta información para personalizar tu consejo táctico.]\n"
        )
        return "\n".join(lines)
