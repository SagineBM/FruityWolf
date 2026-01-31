"""Check that projects have tracks in Library (tracks table)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FruityWolf.database import query

names = ['dfdddd', 'Lmdabza', 'njebded bash nfi9', 'komnditih', 'Fateen']
print("=== Projects and their track count (Library view uses tracks table) ===\n")
for name in names:
    rows = query("""
        SELECT p.id, p.name,
               (SELECT COUNT(*) FROM renders r WHERE r.project_id = p.id) as renders_count,
               (SELECT COUNT(*) FROM tracks t WHERE t.project_id = p.id AND t.ext != '.flp') as tracks_count
        FROM projects p
        WHERE p.name LIKE ?
    """, (f"%{name}%",))
    for row in rows:
        print(f"  {row['name'][:45]:<45} | renders={row['renders_count']:>3} | tracks (Library)={row['tracks_count']:>3}")

print("\n=== Top 15 tracks by file_created_at (what Library shows, newest first) ===")
rows = query("""
    SELECT t.id, t.title, p.name as project_name,
           datetime(t.file_created_at, 'unixepoch', 'localtime') as file_created_dt
    FROM tracks t
    JOIN projects p ON t.project_id = p.id
    WHERE t.ext != '.flp'
    ORDER BY COALESCE(t.file_created_at, t.created_at) DESC
    LIMIT 15
""")
for row in rows:
    print(f"  {row['title'][:35]:<35} | {row['project_name'][:25]:<25} | {row['file_created_dt']}")
