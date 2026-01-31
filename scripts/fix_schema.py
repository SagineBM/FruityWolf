"""
Fix missing database columns/tables.
Run: python scripts/fix_schema.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import get_db, query_one

def main():
    print("Checking and fixing database schema...")
    
    db = get_db()
    
    # Check primary_render_id column
    print("\n1. Checking primary_render_id column...")
    try:
        test_col = query_one("SELECT primary_render_id FROM projects LIMIT 1")
        print("[OK] primary_render_id column exists")
    except Exception as e:
        print(f"[MISSING] primary_render_id column does not exist: {e}")
        print("Adding primary_render_id column...")
        try:
            db.connection.execute("ALTER TABLE projects ADD COLUMN primary_render_id INTEGER REFERENCES renders(id)")
            db.connection.commit()
            print("[OK] Added primary_render_id column successfully!")
        except Exception as e2:
            print(f"[ERROR] Failed to add column: {e2}")
    
    # Check renders table
    print("\n2. Checking renders table...")
    renders_table = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='renders'")
    if renders_table:
        print("[OK] Renders table exists")
        
        # Check file_created_at column in renders
        print("\n3. Checking file_created_at column in renders...")
        try:
            test_col = query_one("SELECT file_created_at FROM renders LIMIT 1")
            print("[OK] file_created_at column exists in renders")
        except:
            print("[MISSING] file_created_at column does not exist in renders")
            print("Adding file_created_at column...")
            try:
                db.connection.execute("ALTER TABLE renders ADD COLUMN file_created_at INTEGER")
                db.connection.commit()
                print("[OK] Added file_created_at column to renders successfully!")
            except Exception as e:
                print(f"[ERROR] Failed to add column: {e}")
    else:
        print("[ERROR] Renders table does NOT exist")
    
    print("\nSchema check complete!")

if __name__ == '__main__':
    main()
