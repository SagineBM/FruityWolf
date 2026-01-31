"""
Database Models and Initialization

SQLite database schema for FL Library Pro.
"""

import os
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def get_app_data_path() -> Path:
    """Get the application data directory."""
    if os.name == 'nt':  # Windows
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    else:  # Linux/Mac
        base = Path.home() / '.config'
    
    app_dir = base / 'FL Library Pro'
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_cache_path() -> Path:
    """Get the cache directory for waveforms and thumbnails."""
    cache_dir = get_app_data_path() / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_db_path() -> Path:
    """Get the database file path."""
    return get_app_data_path() / 'library.db'


# SQL Schema
SCHEMA = """
-- Projects table: FL Studio project folders
-- Projects table: FL Studio project folders
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    flp_path TEXT,
    audio_dir TEXT,
    samples_dir TEXT,
    stems_dir TEXT,
    backup_dir TEXT,
    last_scan INTEGER,
    
    -- Classification & Signals (Phase 1 Core)
    state_id TEXT,
    state_confidence REAL DEFAULT 0.0,
    state_reason TEXT,    -- JSON List
    
    score INTEGER DEFAULT 0,  -- Completion Score
    score_breakdown TEXT, -- JSON Dict
    
    next_action_id TEXT,
    next_action_meta TEXT,   -- JSON Dict
    next_action_reason TEXT, -- JSON List
    
    signals TEXT,         -- JSON { raw, derived }
    user_meta TEXT,       -- JSON { vision, moods, energy, todo }
    
    last_played_ts INTEGER,
    classified_at_ts INTEGER,
    ruleset_hash TEXT,
    
    -- Legacy / Optional
    state TEXT, 
    render_priority_score INTEGER DEFAULT 0,
    needs_render INTEGER DEFAULT 0,
    
    backup_count INTEGER DEFAULT 0,
    samples_count INTEGER DEFAULT 0,
    stems_count INTEGER DEFAULT 0,
    flp_size_kb INTEGER DEFAULT 0,
    
    -- FLP Deep Intelligence (PyFLP)
    flp_tempo REAL,
    flp_time_sig TEXT,
    flp_version TEXT,
    flp_title TEXT,
    flp_artist TEXT,
    flp_genre TEXT,
    flp_pattern_count INTEGER DEFAULT 0,
    flp_parsed_at INTEGER,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Project Plugins (from FLP)
CREATE TABLE IF NOT EXISTS project_plugins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    plugin_name TEXT NOT NULL,
    plugin_type TEXT DEFAULT 'generator',
    channel_index INTEGER,
    mixer_slot INTEGER,
    preset_name TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(project_id, plugin_name, channel_index, mixer_slot)
);

-- Project Samples (from FLP)
CREATE TABLE IF NOT EXISTS project_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    sample_name TEXT NOT NULL,
    sample_path TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    UNIQUE(project_id, sample_path)
);

-- Tracks table: Individual audio files (renders)
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    ext TEXT,
    duration REAL DEFAULT 0,
    file_size INTEGER DEFAULT 0,
    mtime INTEGER,
    
    -- BPM detection
    bpm_detected REAL,
    bpm_user REAL,
    bpm_confidence REAL,
    
    -- Key detection
    key_detected TEXT,
    key_user TEXT,
    key_confidence REAL,
    
    -- Metadata
    notes TEXT,
    favorite INTEGER DEFAULT 0,
    play_count INTEGER DEFAULT 0,
    last_played INTEGER,
    
    -- Cache paths
    waveform_cache_path TEXT,
    cover_path TEXT,
    
    -- Timestamps
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Tags table
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT DEFAULT '#6366f1',
    category TEXT DEFAULT 'custom'  -- 'mood', 'genre', 'custom'
);

-- Track-Tags junction table
CREATE TABLE IF NOT EXISTS track_tags (
    track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (track_id, tag_id)
);

-- Playlists table
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    cover_path TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Playlist tracks junction table
CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
    position INTEGER DEFAULT 0,
    added_at INTEGER DEFAULT (strftime('%s', 'now')),
    PRIMARY KEY (playlist_id, track_id)
);

-- Library roots (multiple folder support)
CREATE TABLE IF NOT EXISTS library_roots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    name TEXT,
    enabled INTEGER DEFAULT 1,
    last_scan INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Indexes for fast search
CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
CREATE INDEX IF NOT EXISTS idx_tracks_favorite ON tracks(favorite);
CREATE INDEX IF NOT EXISTS idx_tracks_project_id ON tracks(project_id);
CREATE INDEX IF NOT EXISTS idx_tracks_bpm ON tracks(COALESCE(bpm_user, bpm_detected));
CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_playlist_tracks_position ON playlist_tracks(playlist_id, position);

-- Optimization Indexes (base schema only; renders/file_created_at indexes are in migrations)
CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_score ON projects(score DESC);
CREATE INDEX IF NOT EXISTS idx_project_plugins_project_name ON project_plugins(project_id, plugin_name);

-- Full-text search virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts USING fts5(
    title, 
    notes,
    content='tracks',
    content_rowid='id'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS tracks_ai AFTER INSERT ON tracks BEGIN
    INSERT INTO tracks_fts(rowid, title, notes) VALUES (new.id, new.title, new.notes);
END;

CREATE TRIGGER IF NOT EXISTS tracks_ad AFTER DELETE ON tracks BEGIN
    INSERT INTO tracks_fts(tracks_fts, rowid, title, notes) VALUES ('delete', old.id, old.title, old.notes);
END;

CREATE TRIGGER IF NOT EXISTS tracks_au AFTER UPDATE ON tracks BEGIN
    INSERT INTO tracks_fts(tracks_fts, rowid, title, notes) VALUES ('delete', old.id, old.title, old.notes);
    INSERT INTO tracks_fts(rowid, title, notes) VALUES (new.id, new.title, new.notes);
END;
"""

# Default tags
DEFAULT_TAGS = [
    # Mood tags
    ('Energetic', '#ef4444', 'mood'),
    ('Chill', '#3b82f6', 'mood'),
    ('Dark', '#1f2937', 'mood'),
    ('Happy', '#fbbf24', 'mood'),
    ('Sad', '#6366f1', 'mood'),
    ('Aggressive', '#dc2626', 'mood'),
    ('Dreamy', '#a855f7', 'mood'),
    ('Epic', '#f97316', 'mood'),
    
    # Genre tags
    ('Trap', '#10b981', 'genre'),
    ('Hip Hop', '#f59e0b', 'genre'),
    ('EDM', '#06b6d4', 'genre'),
    ('House', '#8b5cf6', 'genre'),
    ('Dubstep', '#ec4899', 'genre'),
    ('Pop', '#f472b6', 'genre'),
    ('R&B', '#14b8a6', 'genre'),
    ('Lo-Fi', '#78716c', 'genre'),
    ('Drill', '#64748b', 'genre'),
    ('Afrobeat', '#84cc16', 'genre'),
]


class Database:
    """Database connection and query manager."""
    
    _instance: Optional['Database'] = None
    
    def __new__(cls) -> 'Database':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db_path = get_db_path()
        self._connection: Optional[sqlite3.Connection] = None
        self._initialized = True
        
        # Initialize database
        self.init_db()
    
    @property
    def connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
                timeout=20.0 # Increase timeout
            )
            self._connection.row_factory = sqlite3.Row
            
            # Enable WAL mode for concurrency
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection
    
    @contextmanager
    def cursor(self):
        """Context manager for database cursor."""
        cur = self.connection.cursor()
        try:
            yield cur
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()
    
    def init_db(self):
        """Initialize database schema."""
        from .migrations import run_migrations, MIGRATIONS
        
        # Check if fresh install
        is_fresh = False
        with self.cursor() as cur:
             cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
             if not cur.fetchone():
                 is_fresh = True

        with self.cursor() as cur:
            # Always run schema to ensure base tables exist
            cur.executescript(SCHEMA)
            
            # Insert default tags if not exists
            for name, color, category in DEFAULT_TAGS:
                # ... same logic
                cur.execute(
                    "INSERT OR IGNORE INTO tags (name, color, category) VALUES (?, ?, ?)",
                    (name, color, category)
                )
            
            # Set default settings
            defaults = {
                'theme': 'dark',
                'volume': '0.8',
                'shuffle': '0',
                'repeat': 'none',  # none, one, all
                'waveform_cache_size_mb': '500',
                'auto_scan': '1',
                'fl_studio_path': '',
            }
            for key, value in defaults.items():
                cur.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value)
                )

            # If fresh, ensure version table exists so run_migrations can record applied migrations.
            # Do NOT mark migrations as applied here — run_migrations() must run them to create
            # tables like renders that are not in the base SCHEMA.
            if is_fresh:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        description TEXT,
                        applied_at INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                """)

        # Always run pending migrations (critical for schema updates)
        # This ensures old databases get updated to latest schema
        try:
            migrations_applied = run_migrations(self.connection)
            if migrations_applied > 0:
                logger.info(f"Applied {migrations_applied} database migration(s)")
        except Exception as e:
            logger.critical(f"Critical Migration Error: {e}", exc_info=True)
            # Re-raise to prevent running on broken schema
            raise RuntimeError(f"Database migration failed: {e}") from e
    
    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Convenience functions
def get_db() -> Database:
    """Get the database instance."""
    return Database()


# Transaction management for batch operations
_batch_mode = False
_batch_cursor = None

@contextmanager
def batch_transaction():
    """
    Context manager for batch database operations.
    
    All execute() calls within this context will NOT auto-commit.
    Commits happen at the end of the context (or rollback on exception).
    
    Usage:
        with batch_transaction():
            for item in items:
                execute("INSERT ...", params)  # No auto-commit
            # Auto-commit happens here
    """
    global _batch_mode, _batch_cursor
    
    if _batch_mode:
        # Already in batch mode, just yield
        yield
        return
    
    db = get_db()
    _batch_mode = True
    _batch_cursor = None
    
    try:
        yield
        db.connection.commit()
    except Exception:
        db.connection.rollback()
        raise
    finally:
        _batch_mode = False
        _batch_cursor = None


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """
    Execute a SQL query and return cursor.
    
    If inside a batch_transaction() context, does NOT auto-commit.
    Otherwise, commits immediately after execution.
    """
    global _batch_mode
    
    db = get_db()
    cur = db.connection.cursor()
    cur.execute(sql, params)
    
    # Only auto-commit if not in batch mode
    if not _batch_mode:
        db.connection.commit()
    
    return cur


def execute_many(sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
    """
    Execute a SQL query with multiple parameter sets (executemany).
    
    Much faster than calling execute() in a loop for bulk inserts.
    Commits at the end if not in batch mode.
    """
    global _batch_mode
    
    db = get_db()
    cur = db.connection.cursor()
    cur.executemany(sql, params_list)
    
    if not _batch_mode:
        db.connection.commit()
    
    return cur


def query(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    """Execute a SQL query and return all rows."""
    db = get_db()
    cur = db.connection.cursor()
    cur.execute(sql, params)
    result = cur.fetchall()
    cur.close()
    return result


def query_one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """Execute a SQL query and return one row."""
    db = get_db()
    cur = db.connection.cursor()
    cur.execute(sql, params)
    result = cur.fetchone()
    cur.close()
    return result


# Setting helpers
def get_setting(key: str, default: str = '') -> str:
    """Get a setting value."""
    row = query_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row['value'] if row else default


def set_setting(key: str, value: str):
    """Set a setting value."""
    execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, strftime('%s', 'now'))",
        (key, value)
    )
