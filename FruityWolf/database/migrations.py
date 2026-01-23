"""
FruityWolf Database Migrations

Schema versioning and migration system for upgrading existing databases.
"""

import logging
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
]


# =============================================================================
# Migration Runner
# =============================================================================

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
            
            if migration.up_sql.strip() and not migration.up_sql.strip().startswith('--'):
                self.connection.executescript(migration.up_sql)
            
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
