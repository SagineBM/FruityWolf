"""Check date data in database for debugging sort issues."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import query

print("=== Projects with date info (top 20 by COALESCE(file_created_at, created_at) DESC) ===")
rows = query("""
    SELECT id, name, file_created_at, created_at, 
           datetime(file_created_at, 'unixepoch', 'localtime') as file_created_dt,
           datetime(created_at, 'unixepoch', 'localtime') as created_dt,
           (SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id) as render_count
    FROM projects p
    ORDER BY COALESCE(file_created_at, created_at) DESC
    LIMIT 20
""")

print(f"{'ID':>4} | {'Name':<35} | {'file_created_at':>12} | {'created_at':>12} | {'Renders':>7} | {'File Created DT':<20} | {'Created DT':<20}")
print("-" * 140)
for row in rows:
    name = (row['name'] or '')[:35]
    fc = row['file_created_at'] or 0
    c = row['created_at'] or 0
    fc_dt = row['file_created_dt'] or 'NULL'
    c_dt = row['created_dt'] or 'NULL'
    rc = row['render_count'] or 0
    print(f"{row['id']:>4} | {name:<35} | {fc:>12} | {c:>12} | {rc:>7} | {fc_dt:<20} | {c_dt:<20}")

print("\n=== Tracks with date info (top 20 by COALESCE(file_created_at, created_at) DESC) ===")

# Check if file_created_at column exists in tracks
try:
    query("SELECT file_created_at FROM tracks LIMIT 1")
    has_fc = True
except:
    has_fc = False
    print("NOTE: tracks table does NOT have file_created_at column!")

if has_fc:
    rows = query("""
        SELECT t.id, t.title, t.file_created_at, t.created_at,
               datetime(t.file_created_at, 'unixepoch', 'localtime') as file_created_dt,
               datetime(t.created_at, 'unixepoch', 'localtime') as created_dt
        FROM tracks t
        WHERE t.ext != '.flp'
        ORDER BY COALESCE(t.file_created_at, t.created_at) DESC
        LIMIT 20
    """)
else:
    rows = query("""
        SELECT t.id, t.title, NULL as file_created_at, t.created_at,
               NULL as file_created_dt,
               datetime(t.created_at, 'unixepoch', 'localtime') as created_dt
        FROM tracks t
        WHERE t.ext != '.flp'
        ORDER BY t.created_at DESC
        LIMIT 20
    """)

print(f"{'ID':>6} | {'Title':<35} | {'file_created_at':>12} | {'created_at':>12} | {'File Created DT':<20} | {'Created DT':<20}")
print("-" * 130)
for row in rows:
    title = (row['title'] or '')[:35]
    fc = row['file_created_at'] or 0
    c = row['created_at'] or 0
    fc_dt = row['file_created_dt'] or 'NULL'
    c_dt = row['created_dt'] or 'NULL'
    print(f"{row['id']:>6} | {title:<35} | {fc:>12} | {c:>12} | {fc_dt:<20} | {c_dt:<20}")

print("\n=== Renders with date info (top 20 by COALESCE(file_created_at, mtime) DESC) ===")
try:
    rows = query("""
        SELECT r.id, r.filename, r.project_id, r.file_created_at, r.mtime,
               datetime(r.file_created_at, 'unixepoch', 'localtime') as file_created_dt,
               datetime(r.mtime, 'unixepoch', 'localtime') as mtime_dt
        FROM renders r
        ORDER BY COALESCE(r.file_created_at, r.mtime) DESC
        LIMIT 20
    """)
    
    print(f"{'ID':>6} | {'Filename':<35} | {'ProjID':>6} | {'file_created_at':>12} | {'mtime':>12} | {'File Created DT':<20} | {'Mtime DT':<20}")
    print("-" * 140)
    for row in rows:
        fname = (row['filename'] or '')[:35]
        fc = row['file_created_at'] or 0
        mt = row['mtime'] or 0
        fc_dt = row['file_created_dt'] or 'NULL'
        mt_dt = row['mtime_dt'] or 'NULL'
        print(f"{row['id']:>6} | {fname:<35} | {row['project_id']:>6} | {fc:>12} | {mt:>12} | {fc_dt:<20} | {mt_dt:<20}")
except Exception as e:
    print(f"Error querying renders: {e}")

print("\n=== Stats ===")
# Count NULL file_created_at values
try:
    proj_null = query("SELECT COUNT(*) as cnt FROM projects WHERE file_created_at IS NULL OR file_created_at = 0")[0]['cnt']
    proj_total = query("SELECT COUNT(*) as cnt FROM projects")[0]['cnt']
    print(f"Projects with NULL/0 file_created_at: {proj_null}/{proj_total}")
except Exception as e:
    print(f"Error: {e}")

try:
    track_null = query("SELECT COUNT(*) as cnt FROM tracks WHERE file_created_at IS NULL OR file_created_at = 0")[0]['cnt']
    track_total = query("SELECT COUNT(*) as cnt FROM tracks")[0]['cnt']
    print(f"Tracks with NULL/0 file_created_at: {track_null}/{track_total}")
except Exception as e:
    print(f"Tracks table may not have file_created_at column")

try:
    render_null = query("SELECT COUNT(*) as cnt FROM renders WHERE file_created_at IS NULL OR file_created_at = 0")[0]['cnt']
    render_total = query("SELECT COUNT(*) as cnt FROM renders")[0]['cnt']
    print(f"Renders with NULL/0 file_created_at: {render_null}/{render_total}")
except Exception as e:
    print(f"Error: {e}")
