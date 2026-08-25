import sqlite3
from pathlib import Path

# Go up to repository root
db_path = Path(__file__).parent.parent.parent / "temp_authority_storage" / "authority_join_authorizations.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

print("=== join_authorizations table ===")
cursor.execute("SELECT * FROM join_authorizations")
for row in cursor.fetchall():
    print(row)

print("\n=== challenges table ===")
cursor.execute("SELECT * FROM challenges")
for row in cursor.fetchall():
    print(row)

conn.close()
