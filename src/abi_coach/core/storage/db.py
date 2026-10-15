"""Embedded SQLite Database Manager with WAL mode and thread safety."""

from pathlib import Path
import sqlite3
import threading
from typing import Optional

_LOCAL = threading.local()


class DatabaseManager:
    """Manages thread-local SQLite connections with WAL mode for ultra-low latency."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            cur = Path(__file__).resolve()
            root = None
            for p in cur.parents:
                if (p / "pyproject.toml").is_file():
                    root = p
                    break
            if root is None:
                root = cur.parents[4]
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

                -- ============================================================
                -- Dynamic Topic Archetypes & Contexts (v2 Architecture)
                -- ============================================================
                CREATE TABLE IF NOT EXISTS topic_archetypes (
                    archetype_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    schema_template TEXT NOT NULL,
                    default_system_prompt TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS topic_contexts (
                    context_id TEXT PRIMARY KEY,
                    archetype_id TEXT NOT NULL REFERENCES topic_archetypes(archetype_id),
                    display_name TEXT NOT NULL,
                    current_version TEXT NOT NULL DEFAULT '1.0',
                    config_json TEXT NOT NULL DEFAULT '{}',
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS topic_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT NOT NULL REFERENCES topic_contexts(context_id),
                    category TEXT NOT NULL,
                    entity_key TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    facets_json TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_entities_lookup 
                ON topic_entities(context_id, category, entity_key);

                CREATE VIRTUAL TABLE IF NOT EXISTS topic_entities_fts USING fts5(
                    title,
                    summary,
                    facets_json,
                    content='topic_entities',
                    content_rowid='id'
                );

                CREATE TRIGGER IF NOT EXISTS trg_entities_ai AFTER INSERT ON topic_entities BEGIN
                    INSERT INTO topic_entities_fts(rowid, title, summary, facets_json)
                    VALUES (new.id, new.title, new.summary, new.facets_json);
                END;

                CREATE TRIGGER IF NOT EXISTS trg_entities_ad AFTER DELETE ON topic_entities BEGIN
                    INSERT INTO topic_entities_fts(topic_entities_fts, rowid, title, summary, facets_json)
                    VALUES ('delete', old.id, old.title, old.summary, old.facets_json);
                END;

                CREATE TRIGGER IF NOT EXISTS trg_entities_au AFTER UPDATE ON topic_entities BEGIN
                    INSERT INTO topic_entities_fts(topic_entities_fts, rowid, title, summary, facets_json)
                    VALUES ('delete', old.id, old.title, old.summary, old.facets_json);
                    INSERT INTO topic_entities_fts(rowid, title, summary, facets_json)
                    VALUES (new.id, new.title, new.summary, new.facets_json);
                END;

                CREATE TABLE IF NOT EXISTS engram_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT NOT NULL REFERENCES topic_contexts(context_id),
                    scope TEXT NOT NULL DEFAULT 'project',
                    topic_key TEXT NOT NULL UNIQUE,
                    observation_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    pinned INTEGER DEFAULT 0,
                    access_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_engram_obs_lookup 
                ON engram_observations(context_id, scope, topic_key);

                CREATE TABLE IF NOT EXISTS entity_changelog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_key TEXT NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Seed default archetypes and initial contexts if not present
            self._seed_default_archetypes(con)

    def _seed_default_archetypes(self, con: sqlite3.Connection) -> None:
        """Seed initial foundational archetypes and default contexts."""
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM topic_archetypes;")
        if cur.fetchone()[0] == 0:
            import json

            archetypes = [
                (
                    "extraction_shooter",
                    "Shooter Táctico de Extracción (Loot & Escape)",
                    json.dumps({
                        "categories": ["ammo", "weapon", "armor", "map", "boss", "market_item"],
                        "facets": ["tier", "penetration", "damage", "armor_damage", "velocity", "approx_value", "key_rooms"],
                    }),
                    "Eres un copiloto táctico de élite para shooters de extracción. Prioriza balística, penetración de blindaje, valor de loot por casilla y rutas de extracción seguras.",
                ),
                (
                    "survival_craft",
                    "Supervivencia, Crafteo y Farmeo (MMO/Open World)",
                    json.dumps({
                        "categories": ["silo", "weapon_mod", "crafting_material", "recipe", "boss_drop", "base_defense"],
                        "facets": ["mod_suffix", "drop_chance", "crafting_cost", "durability", "tier", "elemental_damage"],
                    }),
                    "Eres un analista de supervivencia y optimización de recursos. Guía al jugador en calibraciones de armas, drops en silos y gestión de crafteo eficiente.",
                ),
                (
                    "rpg_mmo",
                    "RPG, MMO & Acción Táctica (Builds y Progresión)",
                    json.dumps({
                        "categories": ["skill", "gear_piece", "affix", "dungeon", "raid_mechanic", "talent"],
                        "facets": ["scaling", "cooldown_sec", "stat_reqs", "mana_cost", "synergy", "tier"],
                    }),
                    "Eres un copiloto de progresión y teoría de combate RPG. Optimiza rotaciones, sinergias de habilidades, estadísticas y mecánicas de jefes.",
                ),
                (
                    "general_companion",
                    "Copiloto Universal de Videojuegos & Asistente General",
                    json.dumps({
                        "categories": ["strategy", "keybind", "mechanic", "note", "objective"],
                        "facets": ["priority", "category", "tags", "notes"],
                    }),
                    "Eres Game Advisor, un asistente de videojuegos por voz con IA multimodal para PC. Asiste al jugador en tiempo real en cualquier juego en pantalla.",
                ),
            ]

            con.executemany(
                """
                INSERT INTO topic_archetypes (archetype_id, display_name, schema_template, default_system_prompt)
                VALUES (?, ?, ?, ?);
                """,
                archetypes,
            )

            # Register initial contexts
            contexts = [
                ("abi", "extraction_shooter", "Arena Breakout: Infinite", "S7.0", json.dumps({"primary_resolution": "1440p"}), 1),
                ("generic", "general_companion", "Game Advisor (Universal)", "1.0", json.dumps({}), 0),
                ("once_human", "survival_craft", "Once Human (Silo & Builds)", "1.3", json.dumps({"focus": "mods_and_calibrations"}), 0),
            ]
            con.executemany(
                """
                INSERT OR IGNORE INTO topic_contexts (context_id, archetype_id, display_name, current_version, config_json, is_active)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                contexts,
            )
