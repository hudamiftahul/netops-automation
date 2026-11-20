
import sqlite3
import tempfile
from pathlib import Path

import database
import snmp_scheduler

from alert_engine import (
    initialize_alert_table,
    evaluate_connectivity_alert,
)

# Database sementara
TEST_DB = Path(tempfile.gettempdir()) / "netops_scheduler_test.db"

if TEST_DB.exists():
    TEST_DB.unlink()

# Arahkan database monitoring ke database pengujian
database.DATABASE_FILE = TEST_DB

database.initialize_database()
initialize_alert_table(TEST_DB)


# Simulasi satu perangkat
TEST_DEVICE = [{
    "name": "Router Scheduler Test",
    "ip": "192.0.2.30",
}]


# Simulasi hasil ping untuk tiga siklus
measurements = [
    {
        "status": "OFFLINE",
        "latency_ms": None,
        "packet_loss": 100,
    },
    {
        "status": "OFFLINE",
        "latency_ms": None,
        "packet_loss": 100,
    },
    {
        "status": "ONLINE",
        "latency_ms": 10,
        "packet_loss": 0,
    },
]


def fake_measure_connectivity(ip):
    return measurements.pop(0)


def fake_evaluate_alert(**kwargs):
    return evaluate_connectivity_alert(
        **kwargs,
        db_path=TEST_DB,
    )


# Patch fungsi agar scheduler menggunakan perangkat simulasi
snmp_scheduler.load_inventory_devices = lambda: TEST_DEVICE
snmp_scheduler.measure_connectivity = fake_measure_connectivity
snmp_scheduler.evaluate_connectivity_alert = fake_evaluate_alert


# Jalankan tiga siklus ping monitoring
for cycle in range(1, 4):

    errors = snmp_scheduler.run_ping_monitoring()

    assert errors == 0

    print(f"CYCLE {cycle} PASSED")


# Verifikasi database
with sqlite3.connect(TEST_DB) as connection:

    monitoring_count = connection.execute("""
        SELECT COUNT(*)
        FROM monitoring_history
    """).fetchone()[0]

    alert_rows = connection.execute("""
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

assert monitoring_count == 3
assert len(alert_rows) == 1

alert = alert_rows[0]

assert alert[1] == "OFFLINE"
assert alert[2] == "CRITICAL"
assert alert[3] == "RESOLVED"
assert alert[6] is not None

print("\n===== SCHEDULER INTEGRATION RESULT =====")
print("Monitoring records:", monitoring_count)
print("Alert records:", len(alert_rows))
print("Alert type:", alert[1])
print("Alert severity:", alert[2])
print("Alert status:", alert[3])
print("First seen:", alert[4])
print("Last seen:", alert[5])
print("Resolved at:", alert[6])

print("\nALL SCHEDULER INTEGRATION TESTS PASSED")
