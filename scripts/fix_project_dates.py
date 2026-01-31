"""
Fix missing file_created_at in projects table.

Updates projects with NULL/0 file_created_at by:
1. Using the max file_created_at from their renders
2. Falling back to created_at if no renders
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import query, execute, get_db

def fix_project_dates():
    """Fix missing file_created_at in projects table."""
    
    # Count before
    before_null = query("SELECT COUNT(*) as cnt FROM projects WHERE file_created_at IS NULL OR file_created_at = 0")[0]['cnt']
    total = query("SELECT COUNT(*) as cnt FROM projects")[0]['cnt']
    print(f"Before: {before_null}/{total} projects have NULL/0 file_created_at")
    
    if before_null == 0:
        print("No projects need fixing!")
        return
    
    # Method 1: Update from max render file_created_at
    print("\n1. Updating projects from max render file_created_at...")
    updated_via_renders = execute("""
        UPDATE projects
        SET file_created_at = (
            SELECT MAX(r.file_created_at) 
            FROM renders r 
            WHERE r.project_id = projects.id
              AND r.file_created_at IS NOT NULL 
              AND r.file_created_at > 0
        )
        WHERE (file_created_at IS NULL OR file_created_at = 0)
          AND EXISTS (
              SELECT 1 FROM renders r 
              WHERE r.project_id = projects.id 
                AND r.file_created_at IS NOT NULL 
                AND r.file_created_at > 0
          )
    """).rowcount
    print(f"   Updated {updated_via_renders} projects from renders")
    
    # Method 2: Update remaining from created_at
    print("\n2. Updating remaining projects from created_at...")
    updated_via_created_at = execute("""
        UPDATE projects
        SET file_created_at = created_at
        WHERE (file_created_at IS NULL OR file_created_at = 0)
          AND created_at IS NOT NULL 
          AND created_at > 0
    """).rowcount
    print(f"   Updated {updated_via_created_at} projects from created_at")
    
    # Count after
    after_null = query("SELECT COUNT(*) as cnt FROM projects WHERE file_created_at IS NULL OR file_created_at = 0")[0]['cnt']
    print(f"\nAfter: {after_null}/{total} projects have NULL/0 file_created_at")
    print(f"Fixed: {before_null - after_null} projects")

if __name__ == "__main__":
    db = get_db()  # Initialize database
    fix_project_dates()
