"""Embedded SQLite Database Manager with WAL mode and thread safety."""

import sqlite3
import threading
from pathlib import Path
from typing import Optional

_LOCAL = threading.local()


class DatabaseManager:
    """Manages thread-local SQLite connections with WAL mode for ultra-low latency."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            self.db_path = (root / "data" / "advisor.sqlite3").resolve()
        else:
            self.db_path = Path(db_path).resolve()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection configured for high-concurrency low-latency."""
        if not hasattr(_LOCAL, "connections"):
            _LOCAL.connections = {}
        key = str(self.db_path)
        con = _LOCAL.connections.get(key)
        if con is None:
            con = sqlite3.connect(key, timeout=5.0)
            con.execute("PRAGMA journal_mode = WAL;")
            con.execute("PRAGMA synchronous = NORMAL;")
            con.execute("PRAGMA busy_timeout = 5000;")
            con.execute("PRAGMA foreign_keys = ON;")
            con.row_factory = sqlite3.Row
            _LOCAL.connections[key] = con
        return con

    def _init_database(self) -> None:
        """Create foundational schemas if they do not exist."""
        con = self.get_connection()
        with con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS companion_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    feature TEXT NOT NULL,
                    topic_key TEXT NOT NULL UNIQUE,
                    memory_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    pinned INTEGER DEFAULT 0,
                    access_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_memories_lookup 
                ON companion_memories(game, topic, feature);

                CREATE INDEX IF NOT EXISTS idx_memories_topic_key 
                ON companion_memories(topic_key);

                CREATE TABLE IF NOT EXISTS game_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game TEXT NOT NULL,
                    category TEXT NOT NULL,
                    entity_key TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source TEXT NOT NULL,
                    game_version TEXT NOT NULL DEFAULT 'S7.0',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_knowledge_lookup 
                ON game_knowledge(game, category, entity_key);

                CREATE VIRTUAL TABLE IF NOT EXISTS game_knowledge_fts USING fts5(
                    title,
                    summary,
                    data_json,
                    content='game_knowledge',
                    content_rowid='id'
                );

                CREATE TRIGGER IF NOT EXISTS trg_knowledge_ai AFTER INSERT ON game_knowledge BEGIN
                    INSERT INTO game_knowledge_fts(rowid, title, summary, data_json)
                    VALUES (new.id, new.title, new.summary, new.data_json);
                END;

                CREATE TRIGGER IF NOT EXISTS trg_knowledge_ad AFTER DELETE ON game_knowledge BEGIN
                    INSERT INTO game_knowledge_fts(game_knowledge_fts, rowid, title, summary, data_json)
                    VALUES ('delete', old.id, old.title, old.summary, old.data_json);
                END;

                CREATE TRIGGER IF NOT EXISTS trg_knowledge_au AFTER UPDATE ON game_knowledge BEGIN
                    INSERT INTO game_knowledge_fts(game_knowledge_fts, rowid, title, summary, data_json)
                    VALUES ('delete', old.id, old.title, old.summary, old.data_json);
                    INSERT INTO game_knowledge_fts(rowid, title, summary, data_json)
                    VALUES (new.id, new.title, new.summary, new.data_json);
                END;

                CREATE TABLE IF NOT EXISTS knowledge_changelog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_key TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
