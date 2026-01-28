"""Quick script to check if FabFilter plugins are in the database."""
import sqlite3
from pathlib import Path

db_path = Path.home() / "AppData" / "Roaming" / "FL Library Pro" / "library.db"

if not db_path.exists():
    print(f"Database not found at: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check for FabFilter plugins
cursor.execute("""
    SELECT name, path, format 
    FROM installed_plugins 
    WHERE (name LIKE '%FabFilter%' OR name LIKE '%Pro-Q%' OR name LIKE '%Pro-L%' OR name LIKE '%Pro-C%' OR name LIKE '%Pro-R%')
    AND is_active = 1
    ORDER BY name
    LIMIT 20
""")

rows = cursor.fetchall()
if rows:
    print(f"Found {len(rows)} FabFilter plugins:")
    for row in rows:
        print(f"  - {row['name']} ({row['format']})")
else:
    print("No FabFilter plugins found in database.")
    print("\nChecking all installed plugins...")
    cursor.execute("SELECT COUNT(*) as count FROM installed_plugins WHERE is_active = 1")
    total = cursor.fetchone()['count']
    print(f"Total installed plugins: {total}")

conn.close()
