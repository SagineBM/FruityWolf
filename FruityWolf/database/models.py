"""
Database Models and Initialization

SQLite database schema for FL Library Pro.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


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
    
    -- Classification & Signals
    state TEXT,
    render_priority_score INTEGER DEFAULT 0,
    needs_render INTEGER DEFAULT 0,
    signals TEXT,  -- JSON blob
    backup_count INTEGER DEFAULT 0,
    samples_count INTEGER DEFAULT 0,
    stems_count INTEGER DEFAULT 0,
    flp_size_kb INTEGER DEFAULT 0,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
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
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._connection.row_factory = sqlite3.Row
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
        with self.cursor() as cur:
            cur.executescript(SCHEMA)
            
            # Insert default tags if not exists
            for name, color, category in DEFAULT_TAGS:
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
        
        # Run pending migrations
        from .migrations import run_migrations
        run_migrations(self.connection)
    
    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


# Convenience functions
def get_db() -> Database:
    """Get the database instance."""
    return Database()


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    """Execute a SQL query and return cursor."""
    db = get_db()
    cur = db.connection.cursor()
    cur.execute(sql, params)
    db.connection.commit()
    return cur


def query(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    """Execute a SQL query and return all rows."""
    cur = execute(sql, params)
    result = cur.fetchall()
    cur.close()
    return result


def query_one(sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
    """Execute a SQL query and return one row."""
    cur = execute(sql, params)
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
