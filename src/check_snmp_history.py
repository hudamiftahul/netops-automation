
import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_DIR / "data" / "netops.db"

with sqlite3.connect(DATABASE_FILE) as connection:
    rows = connection.execute("""
        SELECT
            id,
            checked_at,
            device_name,
            ip_address,
            sys_name,
            cpu_usage,
            memory_total,
            memory_used,
            memory_free,
            memory_usage_percent
        FROM snmp_history
        ORDER BY id DESC
        LIMIT 5
    """).fetchall()

print("=== SNMP HISTORY ===")

if not rows:
    print("Belum ada data SNMP.")
else:
    for row in rows:
        print(row)
