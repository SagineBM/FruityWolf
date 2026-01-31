"""
Run database migrations manually.
Run: python scripts/run_migrations.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import get_db
from FruityWolf.database.migrations import run_migrations, MIGRATIONS

def main():
    print("Checking database migrations...")
    
    db = get_db()
    
    # Check current version
    from FruityWolf.database.migrations import MigrationRunner
    runner = MigrationRunner(db.connection)
    current_version = runner.get_current_version()
    
    print(f"Current schema version: {current_version}")
    print(f"Latest migration version: {MIGRATIONS[-1].version}")
    
    if current_version < MIGRATIONS[-1].version:
        print(f"\nRunning migrations {current_version + 1} to {MIGRATIONS[-1].version}...")
        migrations_applied = run_migrations(db.connection)
        print(f"Applied {migrations_applied} migration(s)")
    else:
        print("\nDatabase is up to date!")
    
    # Check if renders table exists
    from FruityWolf.database import query_one
    renders_table = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
    if renders_table:
        print("\n[OK] Renders table exists")
        
        # Count renders
        render_count = query_one("SELECT COUNT(*) as cnt FROM renders")
        print(f"Total renders in database: {render_count['cnt']}")
    else:
        print("\n[ERROR] Renders table does NOT exist")
        print("This means Migration 17 hasn't been applied.")
        print("Checking Migration 17 status...")
        
        # Check if Migration 17 is marked as applied
        migration_17 = query_one("SELECT * FROM schema_version WHERE version = 17")
        if migration_17:
            print(f"Migration 17 is marked as applied: {migration_17}")
            print("But renders table doesn't exist - migration may have failed silently.")
            print("\nAttempting to manually create renders table and add primary_render_id column...")
            try:
                db.connection.executescript("""
                    CREATE TABLE IF NOT EXISTS renders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                        path TEXT NOT NULL UNIQUE,
                        filename TEXT NOT NULL,
                        ext TEXT NOT NULL,
                        file_size INTEGER DEFAULT 0,
                        mtime INTEGER,
                        duration_s REAL DEFAULT 0,
                        fingerprint_fast TEXT,
                        override_key TEXT,
                        override_bpm REAL,
                        label TEXT,
                        is_primary INTEGER DEFAULT 0,
                        file_created_at INTEGER,
                        created_at INTEGER DEFAULT (strftime('%s', 'now')),
                        updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_renders_project ON renders(project_id);
                    CREATE INDEX IF NOT EXISTS idx_renders_primary ON renders(project_id, is_primary);
                    CREATE INDEX IF NOT EXISTS idx_renders_mtime ON renders(mtime DESC);
                """)
                
                # Add primary_render_id column if it doesn't exist
                try:
                    db.connection.execute("ALTER TABLE projects ADD COLUMN primary_render_id INTEGER REFERENCES renders(id)")
                    print("[OK] Added primary_render_id column to projects table")
                except Exception as e:
                    if 'duplicate column' in str(e).lower() or 'already exists' in str(e).lower():
                        print("[INFO] primary_render_id column already exists")
                    else:
                        print(f"[WARNING] Could not add primary_render_id column: {e}")
                
                db.connection.commit()
                print("[OK] Renders table created successfully!")
            except Exception as e:
                print(f"[ERROR] Failed to create renders table: {e}")
        else:
            print("Migration 17 is NOT marked as applied.")
            print("This is unexpected - migrations should have run.")

if __name__ == '__main__':
    main()
