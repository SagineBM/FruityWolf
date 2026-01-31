"""
Fix missing file_created_at in tracks table by copying from renders table.

This is a one-time migration script to fix tracks that have NULL/0 file_created_at
by copying the value from their corresponding render (via render_id or path match).
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import query, execute, get_db

def fix_track_dates():
    """Fix missing file_created_at in tracks table."""
    
    # Count before
    before_null = query("SELECT COUNT(*) as cnt FROM tracks WHERE file_created_at IS NULL OR file_created_at = 0")[0]['cnt']
    total = query("SELECT COUNT(*) as cnt FROM tracks")[0]['cnt']
    print(f"Before: {before_null}/{total} tracks have NULL/0 file_created_at")
    
    if before_null == 0:
        print("No tracks need fixing!")
        return
    
    # Method 1: Update via render_id
    print("\n1. Updating tracks via render_id...")
    updated_via_render_id = execute("""
        UPDATE tracks
        SET file_created_at = (
            SELECT r.file_created_at 
            FROM renders r 
            WHERE r.id = tracks.render_id
        )
        WHERE (file_created_at IS NULL OR file_created_at = 0)
          AND render_id IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM renders r 
              WHERE r.id = tracks.render_id 
                AND r.file_created_at IS NOT NULL 
                AND r.file_created_at > 0
          )
    """).rowcount
    print(f"   Updated {updated_via_render_id} tracks via render_id")
    
    # Method 2: Update via path match
    print("\n2. Updating tracks via path match...")
    updated_via_path = execute("""
        UPDATE tracks
        SET file_created_at = (
            SELECT r.file_created_at 
            FROM renders r 
            WHERE r.path = tracks.path
            LIMIT 1
        )
        WHERE (file_created_at IS NULL OR file_created_at = 0)
          AND EXISTS (
              SELECT 1 FROM renders r 
              WHERE r.path = tracks.path 
                AND r.file_created_at IS NOT NULL 
                AND r.file_created_at > 0
          )
    """).rowcount
    print(f"   Updated {updated_via_path} tracks via path match")
    
    # Method 3: Update remaining from mtime if available
    print("\n3. Updating remaining tracks from mtime...")
    updated_via_mtime = execute("""
        UPDATE tracks
        SET file_created_at = mtime
        WHERE (file_created_at IS NULL OR file_created_at = 0)
          AND mtime IS NOT NULL 
          AND mtime > 0
    """).rowcount
    print(f"   Updated {updated_via_mtime} tracks via mtime")
    
    # Count after
    after_null = query("SELECT COUNT(*) as cnt FROM tracks WHERE file_created_at IS NULL OR file_created_at = 0")[0]['cnt']
    print(f"\nAfter: {after_null}/{total} tracks have NULL/0 file_created_at")
    print(f"Fixed: {before_null - after_null} tracks")
    
    if after_null > 0:
        print(f"\nNote: {after_null} tracks still have no file_created_at (no render data, no mtime)")

if __name__ == "__main__":
    db = get_db()  # Initialize database
    fix_track_dates()
