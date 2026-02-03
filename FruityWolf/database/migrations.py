"""
FruityWolf Database Migrations

Schema versioning and migration system for upgrading existing databases.
"""

import logging
import sqlite3
from typing import List, Callable, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a single database migration."""
    version: int
    description: str
    up_sql: str
    down_sql: Optional[str] = None


# =============================================================================
# Migration Definitions
# =============================================================================

MIGRATIONS: List[Migration] = [
    # Migration 1: Initial schema (already handled by models.py)
    Migration(
        version=1,
        description="Initial schema with projects, tracks, tags, playlists",
        up_sql="-- Initial schema handled by models.py SCHEMA constant",
        down_sql=None
    ),
    
    # Migration 2: Add schema_version table and new indexes
    Migration(
        version=2,
        description="Add schema_version table and performance indexes",
        up_sql="""
        -- Schema version tracking table
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            description TEXT,
            applied_at INTEGER DEFAULT (strftime('%s', 'now'))
        );
        
        -- Additional performance indexes
        CREATE INDEX IF NOT EXISTS idx_tracks_notes ON tracks(notes) WHERE notes IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_tracks_mtime ON tracks(mtime);
        CREATE INDEX IF NOT EXISTS idx_track_tags_track ON track_tags(track_id);
        CREATE INDEX IF NOT EXISTS idx_track_tags_tag ON track_tags(tag_id);
        """,
        down_sql="""
        DROP TABLE IF EXISTS schema_version;
        DROP INDEX IF EXISTS idx_tracks_notes;
        DROP INDEX IF EXISTS idx_tracks_mtime;
        DROP INDEX IF EXISTS idx_track_tags_track;
        DROP INDEX IF EXISTS idx_track_tags_tag;
        """
    ),
    
    # Migration 3: Add more mood/genre tags
    Migration(
        version=3,
        description="Add extended mood and genre tags",
        up_sql="""
        -- Extended mood tags
        INSERT OR IGNORE INTO tags (name, color, category) VALUES 
            ('Rage', '#ef4444', 'mood'),
            ('Afro', '#f59e0b', 'mood'),
            ('Club', '#ec4899', 'mood'),
            ('Cinematic', '#8b5cf6', 'mood'),
            ('Upbeat', '#22c55e', 'mood'),
            ('Melodic', '#3b82f6', 'mood'),
            ('Ethereal', '#a855f7', 'mood'),
            ('Hype', '#f97316', 'mood'),
            ('Bouncy', '#06b6d4', 'mood'),
            ('Ambient', '#94a3b8', 'mood');
        
        -- Extended genre tags
        INSERT OR IGNORE INTO tags (name, color, category) VALUES 
            ('Reggaeton', '#10b981', 'genre'),
            ('Soul', '#8b5cf6', 'genre'),
            ('Jazz', '#0ea5e9', 'genre'),
            ('Rock', '#ef4444', 'genre'),
            ('Future Bass', '#22d3ee', 'genre'),
            ('Phonk', '#be185d', 'genre'),
            ('UK Drill', '#475569', 'genre'),
            ('Amapiano', '#facc15', 'genre');
        """,
        down_sql=None  # Tags are not removed on downgrade
    ),
    
    # Migration 4: Add play history tracking
    Migration(
        version=4,
        description="Add play history and rating support",
        up_sql="""
        -- Play history table
        CREATE TABLE IF NOT EXISTS play_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER REFERENCES tracks(id) ON DELETE CASCADE,
            played_at INTEGER DEFAULT (strftime('%s', 'now')),
            position_at_end REAL DEFAULT 0
        );
        
        CREATE INDEX IF NOT EXISTS idx_play_history_track ON play_history(track_id);
        CREATE INDEX IF NOT EXISTS idx_play_history_date ON play_history(played_at);
        
        -- Add rating column to tracks
        ALTER TABLE tracks ADD COLUMN rating INTEGER DEFAULT 0;
        """,
        down_sql="""
        DROP TABLE IF EXISTS play_history;
        """
    ),
    
    # Migration 5: Add Project State Classification
    Migration(
        version=5,
        description="Add project state classification columns",
        up_sql="""
        ALTER TABLE tracks ADD COLUMN state TEXT;
        ALTER TABLE tracks ADD COLUMN state_reason TEXT;
        ALTER TABLE tracks ADD COLUMN manual_state TEXT;
        ALTER TABLE tracks ADD COLUMN labels TEXT;
        
        CREATE INDEX IF NOT EXISTS idx_tracks_state ON tracks(state);
        """,
        down_sql="""
        -- SQLite does not support dropping columns easily, so we usually ignore or rebuild
        -- For safety we assume down migration just ignores them or requires manual handling
        """
    ),
    
    # Migration 6: Add user_dead column for classifier
    Migration(
        version=6,
        description="Add user_dead column for classifier dead override",
        up_sql="""
        ALTER TABLE tracks ADD COLUMN user_dead INTEGER DEFAULT 0;
        """,
        down_sql=""
    ),
    
    # Migration 7: Add lyrics column to tracks table
    Migration(
        version=7,
        description="Add lyrics column to tracks table",
        up_sql="""
        ALTER TABLE tracks ADD COLUMN lyrics TEXT;
        """,
        down_sql=""
    ),

    # Migration 8: Add project signals and classification
    Migration(
        version=8,
        description="Add project classification signals and score",
        up_sql="""
        ALTER TABLE projects ADD COLUMN state TEXT;
        ALTER TABLE projects ADD COLUMN render_priority_score INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN needs_render INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN signals TEXT;  -- JSON blob for detailed signals
        
        -- Add individual signal columns for easier querying if needed
        ALTER TABLE projects ADD COLUMN backup_count INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN samples_count INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN stems_count INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN flp_size_kb INTEGER DEFAULT 0;
        """,
        down_sql="""
        -- Cannot drop columns in SQLite easily
        """
    ),
    
    # Migration 9: Phase 1 Core - Robust Classification Columns
    Migration(
        version=9,
        description="Add robust Phase 1 classification columns (State ID, Score, Next Action, Meta)",
        up_sql="""
        ALTER TABLE projects ADD COLUMN state_id TEXT;
        ALTER TABLE projects ADD COLUMN state_confidence REAL DEFAULT 0.0;
        ALTER TABLE projects ADD COLUMN state_reason TEXT;
        
        ALTER TABLE projects ADD COLUMN score INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN score_breakdown TEXT;
        
        ALTER TABLE projects ADD COLUMN next_action_id TEXT;
        ALTER TABLE projects ADD COLUMN next_action_meta TEXT;
        ALTER TABLE projects ADD COLUMN next_action_reason TEXT;
        
        ALTER TABLE projects ADD COLUMN user_meta TEXT;
        
        ALTER TABLE projects ADD COLUMN last_played_ts INTEGER;
        ALTER TABLE projects ADD COLUMN classified_at_ts INTEGER;
        ALTER TABLE projects ADD COLUMN ruleset_hash TEXT;
        """,
        down_sql=""
    ),
    
    # Migration 10: Phase 2 - Sample Usage Indexing
    Migration(
        version=10,
        description="Add project_samples table for organization intelligence",
        up_sql="""
        CREATE TABLE IF NOT EXISTS project_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            sample_name TEXT NOT NULL,
            sample_path TEXT NOT NULL,
            UNIQUE(project_id, sample_path)
        );
        CREATE INDEX IF NOT EXISTS idx_project_samples_name ON project_samples(sample_name);
        CREATE INDEX IF NOT EXISTS idx_project_samples_project ON project_samples(project_id);
        """,
        down_sql="DROP TABLE IF EXISTS project_samples;"
    ),
    
    # Migration 11: PyFLP Integration - Plugin Tracking & FLP Metadata
    Migration(
        version=11,
        description="Add FLP metadata columns and plugin/sample identification tables",
        up_sql="""
        -- Plugins used in projects
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
        
        CREATE INDEX IF NOT EXISTS idx_project_plugins_name ON project_plugins(plugin_name);
        CREATE INDEX IF NOT EXISTS idx_project_plugins_project ON project_plugins(project_id);
        
        -- Add FLP metadata columns (one by one for robustness)
        -- We use INSERT OR IGNORE patterns if they existed but they don't in ALTER TABLE.
        -- We will wrap these in try/except in a separate script or just rely on the fact 
        -- that they are missing now.
        ALTER TABLE projects ADD COLUMN flp_tempo REAL;
        ALTER TABLE projects ADD COLUMN flp_time_sig TEXT;
        ALTER TABLE projects ADD COLUMN flp_version TEXT;
        ALTER TABLE projects ADD COLUMN flp_title TEXT;
        ALTER TABLE projects ADD COLUMN flp_artist TEXT;
        ALTER TABLE projects ADD COLUMN flp_genre TEXT;
        ALTER TABLE projects ADD COLUMN flp_pattern_count INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN flp_parsed_at INTEGER;
        
        -- Additional indexes
        CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
        CREATE INDEX IF NOT EXISTS idx_projects_state_id ON projects(state_id);
        """,
        down_sql="DROP TABLE IF EXISTS project_plugins;"
    ),

    # Migration 12: System-wide Plugin Tracking
    Migration(
        version=12,
        description="Add installed_plugins table for system-wide VST tracking",
        up_sql="""
        CREATE TABLE IF NOT EXISTS installed_plugins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT NOT NULL UNIQUE,
            category TEXT, -- 'generator', 'effect', 'unknown'
            format TEXT, -- 'VST', 'VST3', 'CLAP', 'Native'
            vendor TEXT,
            is_active INTEGER DEFAULT 1,
            last_seen INTEGER,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        );
        CREATE INDEX IF NOT EXISTS idx_installed_plugins_name ON installed_plugins(name);
        CREATE INDEX IF NOT EXISTS idx_installed_plugins_format ON installed_plugins(format);
        """,
        down_sql="DROP TABLE IF EXISTS installed_plugins;"
    ),

    # Migration 13: Detailed Plugin Info
    Migration(
        version=13,
        description="Add plugin_path column to track binary locations",
        up_sql="""
        ALTER TABLE project_plugins ADD COLUMN plugin_path TEXT;
        """,
        down_sql=""
    ),

    # Migration 14: Custom Plugin Scan Roots
    Migration(
        version=14,
        description="Add plugin_scan_roots table for custom search paths",
        up_sql="""
        CREATE TABLE IF NOT EXISTS plugin_scan_roots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            name TEXT,
            enabled INTEGER DEFAULT 1,
            created_at INTEGER DEFAULT (strftime('%s', 'now'))
        );
        """,
        down_sql="DROP TABLE IF EXISTS plugin_scan_roots;"
    ),

    # Migration 15: Plugin Metadata expansion
    Migration(
        version=15,
        description="Expand installed_plugins with production-grade metadata",
        up_sql="""
        ALTER TABLE installed_plugins ADD COLUMN arch TEXT;
        ALTER TABLE installed_plugins ADD COLUMN is_shell INTEGER DEFAULT 0;
        ALTER TABLE installed_plugins ADD COLUMN exports_validated INTEGER DEFAULT 0;
        ALTER TABLE installed_plugins ADD COLUMN content_related INTEGER DEFAULT 0;
        ALTER TABLE installed_plugins ADD COLUMN plugin_type_tag TEXT;
        """,
        down_sql=""
    ),
    
    # Migration 16: Production-Grade Plugin Detection (already covered by Migration 15)
    # This migration is a no-op as Migration 15 already added all required columns
    Migration(
        version=16,
        description="Production-grade plugin detection support (columns already exist)",
        up_sql="""
        -- Columns already exist from Migration 15
        -- This migration ensures schema is up to date
        """,
        down_sql=""
    ),
    
    # Migration 17: FL Studio Render System
    Migration(
        version=17,
        description="Add renders table and primary_render_id for proper FL Studio project structure",
        up_sql="""
        -- Renders table: Audio files that are actual project renders/exports
        CREATE TABLE IF NOT EXISTS renders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            path TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            ext TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            mtime INTEGER,
            duration_s REAL DEFAULT 0,
            fingerprint_fast TEXT,  -- Hash of (size, mtime) for caching
            override_key TEXT,
            override_bpm REAL,
            label TEXT,  -- User-assigned label (e.g., "v1", "final", "best chorus")
            is_primary INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            updated_at INTEGER DEFAULT (strftime('%s', 'now'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_renders_project ON renders(project_id);
        CREATE INDEX IF NOT EXISTS idx_renders_primary ON renders(project_id, is_primary);
        CREATE INDEX IF NOT EXISTS idx_renders_mtime ON renders(mtime DESC);
        
        -- Add primary_render_id to projects table
        ALTER TABLE projects ADD COLUMN primary_render_id INTEGER REFERENCES renders(id);
        
        -- Migrate existing tracks to renders (if they're root-level audio)
        -- This is a best-effort migration - we'll mark tracks as renders if they're in project root
        INSERT INTO renders (project_id, path, filename, ext, file_size, mtime, duration_s, created_at, updated_at)
        SELECT 
            t.project_id,
            t.path,
            t.title || t.ext as filename,
            t.ext,
            t.file_size,
            t.mtime,
            t.duration,
            t.created_at,
            t.updated_at
        FROM tracks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.ext IN ('.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aiff', '.aif')
        AND t.path NOT LIKE '%/Audio/%'
        AND t.path NOT LIKE '%\\Audio\\%'
        AND t.path NOT LIKE '%/Samples/%'
        AND t.path NOT LIKE '%\\Samples\\%'
        AND t.path NOT LIKE '%/Backup/%'
        AND t.path NOT LIKE '%\\Backup\\%'
        AND NOT EXISTS (SELECT 1 FROM renders r WHERE r.path = t.path);
        
        -- Set primary render for projects that have renders
        UPDATE projects SET primary_render_id = (
            SELECT r.id FROM renders r 
            WHERE r.project_id = projects.id 
            ORDER BY r.mtime DESC 
            LIMIT 1
        ) WHERE primary_render_id IS NULL;
        """,
        down_sql="""
        ALTER TABLE projects DROP COLUMN primary_render_id;
        DROP TABLE IF EXISTS renders;
        """
    ),
    
    # Migration 18: Enhanced Tracks for All Renders
    Migration(
        version=18,
        description="Add render_id and is_primary to tracks for full render indexing",
        up_sql="""
        -- Add render_id to link tracks to renders
        ALTER TABLE tracks ADD COLUMN render_id INTEGER REFERENCES renders(id);
        
        -- Add is_primary flag for quick primary identification
        ALTER TABLE tracks ADD COLUMN is_primary INTEGER DEFAULT 0;
        
        -- Create unique index on render_id to prevent duplicates across rescans
        CREATE UNIQUE INDEX IF NOT EXISTS idx_tracks_render_id_unique ON tracks(render_id) WHERE render_id IS NOT NULL;
        
        -- Add index on project_id for efficient project-based queries
        CREATE INDEX IF NOT EXISTS idx_tracks_project_id ON tracks(project_id);
        
        -- Add index on title for search performance
        CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title);
        
        -- Backfill: Link existing tracks to renders by matching path
        UPDATE tracks SET render_id = (
            SELECT r.id FROM renders r WHERE r.path = tracks.path LIMIT 1
        ) WHERE render_id IS NULL;
        
        -- Mark existing tracks as primary if they match project's primary render
        UPDATE tracks SET is_primary = 1 
        WHERE render_id IS NOT NULL 
        AND render_id IN (SELECT primary_render_id FROM projects WHERE primary_render_id IS NOT NULL);
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_tracks_render_id_unique;
        DROP INDEX IF EXISTS idx_tracks_project_id;
        DROP INDEX IF EXISTS idx_tracks_title;
        """
    ),
    
    # Migration 19: Original File Creation Date
    Migration(
        version=19,
        description="Add file_created_at column for original file creation date sorting",
        up_sql="""
        -- Add file_created_at to projects (from FLP or oldest render)
        ALTER TABLE projects ADD COLUMN file_created_at INTEGER;
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_projects_file_created;
        """
    ),
    
    # Migration 20: file_created_at for tracks
    Migration(
        version=20,
        description="Add file_created_at column to tracks for sorting",
        up_sql="""
        ALTER TABLE tracks ADD COLUMN file_created_at INTEGER;
        CREATE INDEX IF NOT EXISTS idx_tracks_file_created ON tracks(file_created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_projects_file_created ON projects(file_created_at DESC);
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_tracks_file_created;
        """
    ),
    
    # Migration 21: file_created_at for renders (optional, only if renders table exists)
    Migration(
        version=21,
        description="Add file_created_at column to renders for sorting",
        up_sql="""
        ALTER TABLE renders ADD COLUMN file_created_at INTEGER;
        CREATE INDEX IF NOT EXISTS idx_renders_file_created ON renders(file_created_at DESC);
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_renders_file_created;
        """
    ),
    
    # Migration 22: Custom Cover Art Support
    Migration(
        version=22,
        description="Add custom_cover_path to projects table for user-uploaded covers",
        up_sql="""
        -- Add custom cover path to projects
        ALTER TABLE projects ADD COLUMN custom_cover_path TEXT;
        
        -- Note: tracks.cover_path and playlists.cover_path already exist
        -- This migration adds support for project-level custom covers
        """,
        down_sql=""
    ),
    
    # Migration 23: Identity System - Project Identity Layer
    Migration(
        version=23,
        description="Add identity system tables and columns for project identity, file tracking, signals, and metadata review",
        up_sql="""
        -- Add identity columns to projects table
        -- Note: SQLite doesn't support UNIQUE constraint in ALTER TABLE ADD COLUMN
        -- We'll add the column first, then create a unique index
        ALTER TABLE projects ADD COLUMN pid TEXT;
        ALTER TABLE projects ADD COLUMN confidence_score INTEGER DEFAULT 100;
        ALTER TABLE projects ADD COLUMN user_locked INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN daw_type TEXT DEFAULT 'fl_studio';
        
        -- Create unique index on pid for fast lookups (enforces uniqueness)
        CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_pid_unique ON projects(pid) WHERE pid IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_projects_pid ON projects(pid);
        CREATE INDEX IF NOT EXISTS idx_projects_confidence ON projects(confidence_score);
        CREATE INDEX IF NOT EXISTS idx_projects_user_locked ON projects(user_locked);
        
        -- project_files table: Source of truth for all files associated with a project
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            file_path TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            file_hash TEXT NULL,
            file_role TEXT NOT NULL,
            file_ext TEXT,
            file_size INTEGER,
            file_mtime INTEGER,
            is_primary INTEGER DEFAULT 0,
            confidence_score INTEGER DEFAULT 100,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            last_seen INTEGER DEFAULT (strftime('%s', 'now')),
            UNIQUE(project_id, file_path)
        );
        
        -- Indexes for project_files
        CREATE INDEX IF NOT EXISTS idx_project_files_project ON project_files(project_id);
        CREATE INDEX IF NOT EXISTS idx_project_files_role ON project_files(file_role);
        CREATE INDEX IF NOT EXISTS idx_project_files_fingerprint ON project_files(fingerprint);
        CREATE INDEX IF NOT EXISTS idx_project_files_path ON project_files(file_path);
        CREATE INDEX IF NOT EXISTS idx_project_files_primary ON project_files(project_id, is_primary) WHERE is_primary = 1;
        
        -- file_signals table: Evidence signals for file matching and attribution
        CREATE TABLE IF NOT EXISTS file_signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL REFERENCES project_files(id) ON DELETE CASCADE,
            signal_type TEXT NOT NULL,
            signal_value_text TEXT NULL,
            signal_value_num REAL NULL,
            weight INTEGER DEFAULT 10,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            UNIQUE(file_id, signal_type)
        );
        
        -- Indexes for file_signals
        CREATE INDEX IF NOT EXISTS idx_file_signals_file ON file_signals(file_id);
        CREATE INDEX IF NOT EXISTS idx_file_signals_type ON file_signals(signal_type);
        
        -- metadata_review_queue table: Queue for metadata changes that need user review
        CREATE TABLE IF NOT EXISTS metadata_review_queue (
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            field TEXT NOT NULL,
            suggested_value TEXT NOT NULL,
            confidence INTEGER NOT NULL,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            PRIMARY KEY (project_id, field)
        );
        
        CREATE INDEX IF NOT EXISTS idx_metadata_review_project ON metadata_review_queue(project_id);
        
        -- Generate PIDs for existing projects (if any)
        -- Using random UUIDs would require Python, so we'll do this in code during migration
        -- For now, leave pid NULL - it will be populated during first scan
        """,
        down_sql="""
        -- Note: SQLite doesn't support dropping columns easily
        -- These tables can be dropped if needed, but columns remain
        DROP TABLE IF EXISTS metadata_review_queue;
        DROP TABLE IF EXISTS file_signals;
        DROP TABLE IF EXISTS project_files;
        DROP INDEX IF EXISTS idx_projects_pid;
        DROP INDEX IF EXISTS idx_projects_confidence;
        DROP INDEX IF EXISTS idx_projects_user_locked;
        """
    ),

    # Migration 24: Add Missing Performance Indexes
    Migration(
        version=24,
        description="Add missing indexes for optimizing sort and search performance",
        up_sql="""
        -- Optimize 'Recently Updated' sort
        CREATE INDEX IF NOT EXISTS idx_projects_updated_at ON projects(updated_at DESC);
        
        -- Optimize 'Completion Score' sort
        CREATE INDEX IF NOT EXISTS idx_projects_score ON projects(score DESC);
        
        -- Optimize render lookups by project and mtime
        CREATE INDEX IF NOT EXISTS idx_renders_project_mtime ON renders(project_id, mtime DESC);
        
        -- Optimize plugin lookups by project
        CREATE INDEX IF NOT EXISTS idx_project_plugins_project_name ON project_plugins(project_id, plugin_name);
        
        -- Optimize file_created_at sort for unified library view
        CREATE INDEX IF NOT EXISTS idx_tracks_file_created_at_desc ON tracks(file_created_at DESC);
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_projects_updated_at;
        DROP INDEX IF EXISTS idx_projects_score;
        DROP INDEX IF EXISTS idx_renders_project_mtime;
        DROP INDEX IF EXISTS idx_project_plugins_project_name;
        DROP INDEX IF EXISTS idx_tracks_file_created_at_desc;
        """
    ),
    
    # Migration 25: Render Status Column
    Migration(
        version=25,
        description="Add render_status column to projects for explicit state tracking",
        up_sql="""
        -- render_status: unheard, rendering, preview_ready, render_failed
        ALTER TABLE projects ADD COLUMN render_status TEXT DEFAULT 'unheard';
        CREATE INDEX IF NOT EXISTS idx_projects_render_status ON projects(render_status);
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_projects_render_status;
        """
    ),
    
    # Migration 26: Activity Heat and Safety Signals
    Migration(
        version=26,
        description="Add Activity Heat, Audibility, and Safety columns",
        up_sql="""
        -- Tracking columns for Activity Heat
        ALTER TABLE projects ADD COLUMN last_opened_at INTEGER;
        ALTER TABLE projects ADD COLUMN open_count INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN play_count INTEGER DEFAULT 0;
        
        -- Tracking columns for Safety/Rendering History
        ALTER TABLE projects ADD COLUMN last_rendered_at INTEGER;
        ALTER TABLE projects ADD COLUMN render_attempted_count INTEGER DEFAULT 0;
        ALTER TABLE projects ADD COLUMN last_render_failed_at INTEGER;
        ALTER TABLE projects ADD COLUMN last_render_failed_reason TEXT;
        
        -- Backfill last_rendered_at from renders table (best effort)
        UPDATE projects 
        SET last_rendered_at = (
            SELECT MAX(r.mtime) 
            FROM renders r 
            WHERE r.project_id = projects.id
        )
        WHERE last_rendered_at IS NULL;
        
        -- Index for sorting/filtering
        CREATE INDEX IF NOT EXISTS idx_projects_last_opened ON projects(last_opened_at DESC);
        """,
        down_sql="""
        DROP INDEX IF EXISTS idx_projects_last_opened;
        """
    ),
    
    # Migration 27: Plugin Alias Overrides
    Migration(
        version=27,
        description="Add plugin_alias_overrides table for user-defined plugin matching",
        up_sql="""
        CREATE TABLE IF NOT EXISTS plugin_alias_overrides (
            ref_key TEXT PRIMARY KEY, -- lower(ref_raw)|ref_type
            ref_raw TEXT NOT NULL,
            ref_canon TEXT,
            ref_type TEXT,
            chosen_installed_id INTEGER,
            created_at INTEGER DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY(chosen_installed_id) REFERENCES installed_plugins(id) ON DELETE CASCADE
        );
        """,
        down_sql="""
        DROP TABLE IF EXISTS plugin_alias_overrides;
        """
    ),
    Migration(
        version=28,
        description="Index installed_plugins(is_active) for plugin truth-state and safe-to-open queries",
        up_sql="CREATE INDEX IF NOT EXISTS idx_installed_plugins_is_active ON installed_plugins(is_active) WHERE is_active = 1;",
        down_sql="DROP INDEX IF EXISTS idx_installed_plugins_is_active;"
    ),
]


class MigrationRunner:
    """Runs database migrations to keep schema up to date."""
    
    def __init__(self, connection):
        self.connection = connection
        self._ensure_version_table()
    
    def _ensure_version_table(self):
        """Ensure schema_version table exists."""
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT,
                applied_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)
        self.connection.commit()
    
    def get_current_version(self) -> int:
        """Get the current schema version."""
        cursor = self.connection.execute(
            "SELECT MAX(version) as version FROM schema_version"
        )
        row = cursor.fetchone()
        return row[0] or 0 if row else 0
    
    def get_applied_migrations(self) -> List[int]:
        """Get list of applied migration versions."""
        cursor = self.connection.execute(
            "SELECT version FROM schema_version ORDER BY version"
        )
        return [row[0] for row in cursor.fetchall()]
    
    def run_migration(self, migration: Migration) -> bool:
        """Run a single migration."""
        try:
            logger.info(f"Applying migration {migration.version}: {migration.description}")
            
            # Check if SQL has actual statements (not just comments)
            sql_lines = [line.strip() for line in migration.up_sql.split('\n') if line.strip() and not line.strip().startswith('--')]
            if sql_lines:
                # Handle ALTER TABLE ADD COLUMN gracefully (ignore if column already exists)
                sql = migration.up_sql
                # SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
                # So we'll catch the error and continue
                try:
                    self.connection.executescript(sql)
                except sqlite3.OperationalError as e:
                    error_msg = str(e).lower()
                    # If column already exists, that's okay - continue
                    if 'duplicate column' in error_msg or 'already exists' in error_msg:
                        logger.warning(f"Migration {migration.version}: Column already exists or operation skipped: {e}")
                        # Still mark migration as applied since it's a no-op
                    elif 'no such column' in error_msg:
                        # This is a real error - column doesn't exist when it should
                        logger.error(f"Migration {migration.version}: Column missing error: {e}")
                        raise
                    else:
                        # For other errors, try to continue if it's a non-critical issue
                        # But log it as a warning
                        logger.warning(f"Migration {migration.version}: Operational error (may be non-critical): {e}")
                        # Don't raise - let migration continue, but log the issue
            
            # Record migration
            self.connection.execute(
                "INSERT OR REPLACE INTO schema_version (version, description) VALUES (?, ?)",
                (migration.version, migration.description)
            )
            self.connection.commit()
            
            logger.info(f"Migration {migration.version} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration {migration.version} failed: {e}")
            self.connection.rollback()
            return False
    
    def migrate_to_latest(self) -> int:
        """Run all pending migrations. Returns number of migrations applied."""
        applied = self.get_applied_migrations()
        count = 0
        
        for migration in MIGRATIONS:
            if migration.version not in applied:
                if self.run_migration(migration):
                    count += 1
                else:
                    logger.error(f"Migration stopped at version {migration.version}")
                    break
        
        if count > 0:
            logger.info(f"Applied {count} migration(s). Current version: {self.get_current_version()}")
        else:
            logger.debug("Database schema is up to date")
        
        return count
    
    def rollback(self, target_version: int) -> int:
        """Roll back to a specific version. Returns number of rollbacks performed."""
        current = self.get_current_version()
        if target_version >= current:
            logger.info("Nothing to rollback")
            return 0
        
        count = 0
        # Get migrations in reverse order
        for migration in reversed(MIGRATIONS):
            if migration.version <= target_version:
                break
            if migration.version > current:
                continue
            
            if migration.down_sql:
                try:
                    logger.info(f"Rolling back migration {migration.version}")
                    self.connection.executescript(migration.down_sql)
                    self.connection.execute(
                        "DELETE FROM schema_version WHERE version = ?",
                        (migration.version,)
                    )
                    self.connection.commit()
                    count += 1
                except Exception as e:
                    logger.error(f"Rollback of migration {migration.version} failed: {e}")
                    self.connection.rollback()
                    break
            else:
                logger.warning(f"Migration {migration.version} has no rollback SQL, stopping")
                break
        
        return count


def run_migrations(connection) -> int:
    """Convenience function to run all pending migrations."""
    runner = MigrationRunner(connection)
    return runner.migrate_to_latest()
