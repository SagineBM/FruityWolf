"""Check render data for projects."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import query

# Find projects that have renders
print("=== Projects with renders (checking render_count) ===")
rows = query("""
    SELECT p.id, p.name, 
           (SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id) as actual_render_count,
           datetime(p.file_created_at, 'unixepoch', 'localtime') as file_created_dt
    FROM projects p
    WHERE EXISTS (SELECT 1 FROM renders r WHERE r.project_id = p.id)
    ORDER BY p.file_created_at DESC
    LIMIT 30
""")
print(f"{'ID':>4} | {'Name':<40} | {'Renders':>7} | File Created DT")
print("-" * 80)
for row in rows:
    print(f"{row['id']:>4} | {(row['name'] or '')[:40]:<40} | {row['actual_render_count']:>7} | {row['file_created_dt']}")

# Check for orphan renders
print("\n=== Orphan renders (no matching project) ===")
orphans = query("SELECT COUNT(*) as cnt FROM renders WHERE project_id NOT IN (SELECT id FROM projects)")
print(f"Orphan renders: {orphans[0]['cnt']}")

# Check newest projects overall
print("\n=== Newest 20 projects (by file_created_at) ===")
rows = query("""
    SELECT p.id, p.name, 
           (SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id) as render_count,
           datetime(p.file_created_at, 'unixepoch', 'localtime') as file_created_dt
    FROM projects p
    ORDER BY p.file_created_at DESC
    LIMIT 20
""")
print(f"{'ID':>4} | {'Name':<40} | {'Renders':>7} | File Created DT")
print("-" * 80)
for row in rows:
    print(f"{row['id']:>4} | {(row['name'] or '')[:40]:<40} | {row['render_count']:>7} | {row['file_created_dt']}")
