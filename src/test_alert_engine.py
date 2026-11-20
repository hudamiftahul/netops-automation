
import sqlite3
import tempfile
from pathlib import Path

from alert_engine import (
    initialize_alert_table,
    evaluate_connectivity_alert,
)

# Database sementara agar database monitoring asli tidak terganggu.
TEST_DB = Path(tempfile.gettempdir()) / "netops_alert_test.db"

if TEST_DB.exists():
    TEST_DB.unlink()

initialize_alert_table(TEST_DB)


def evaluate(time, status, latency=None, packet_loss=None):
    evaluate_connectivity_alert(
        checked_at=f"2026-11-18T{time}:00",
        device_name="Router Test",
        ip_address="192.0.2.1",
        status=status,
        latency_ms=latency,
        packet_loss=packet_loss,
        db_path=TEST_DB,
    )


# TEST 1: OFFLINE membuat alert CRITICAL
evaluate("10:00", "OFFLINE")

# TEST 2: OFFLINE berulang tidak membuat alert baru
evaluate("10:05", "OFFLINE")

# TEST 3: ONLINE menyelesaikan alert OFFLINE
evaluate("10:10", "ONLINE", 10, 0)

# TEST 4: OFFLINE kembali membuat alert baru
evaluate("10:15", "OFFLINE")

# TEST 5: ONLINE tetapi latency tinggi
# Alert OFFLINE selesai, HIGH_LATENCY dibuat
evaluate("10:20", "ONLINE", 250, 0)

# TEST 6: Latency masih tinggi, update alert yang sama
evaluate("10:25", "ONLINE", 270, 0)

# TEST 7: Latency normal, alert selesai
evaluate("10:30", "ONLINE", 20, 0)

# TEST 8: Packet loss tinggi
evaluate("10:35", "ONLINE", 20, 30)

# TEST 9: Packet loss normal, alert selesai
evaluate("10:40", "ONLINE", 20, 0)


# Tampilkan hasil
with sqlite3.connect(TEST_DB) as connection:

    rows = connection.execute("""
        SELECT
            id,
            alert_type,
            severity,
            status,
            first_seen,
            last_seen,
            resolved_at
        FROM alert_history
        ORDER BY id
    """).fetchall()

    active_count = connection.execute("""
        SELECT COUNT(*)
        FROM alert_history
        WHERE status = 'ACTIVE'
    """).fetchone()[0]


print("\n===== ALERT HISTORY =====")

for row in rows:
    print(row)

print("\nTotal alerts:", len(rows))
print("Active alerts:", active_count)

# Semua kondisi pengujian di atas sudah kembali normal.
assert len(rows) == 4
assert active_count == 0
assert all(row[3] == "RESOLVED" for row in rows)

print("\nALL TESTS PASSED")
