
import sqlite3
import tempfile
from pathlib import Path

import database

from alert_engine import (
    initialize_alert_table,
    evaluate_connectivity_alert,
)

# Database khusus pengujian
TEST_DB = Path(tempfile.gettempdir()) / "netops_integration_test.db"

if TEST_DB.exists():
    TEST_DB.unlink()

# Arahkan database.py ke database sementara
database.DATABASE_FILE = TEST_DB

# Inisialisasi tabel
database.initialize_database()
initialize_alert_table(TEST_DB)

# Simulasi hasil monitoring perangkat
checked_at = "2026-11-20T10:00:00"
device_name = "Router Integration Test"
ip_address = "192.0.2.20"

status = "OFFLINE"
latency_ms = None
packet_loss = 100

# STEP 1: Simpan hasil monitoring
database.save_result(
    checked_at,
    device_name,
    ip_address,
    status,
    latency_ms,
    packet_loss,
)

print("STEP 1 PASSED: Monitoring result saved")

# STEP 2: Evaluasi alert
events = evaluate_connectivity_alert(
    checked_at=checked_at,
    device_name=device_name,
    ip_address=ip_address,
    status=status,
    latency_ms=latency_ms,
    packet_loss=packet_loss,
    db_path=TEST_DB,
)

assert len(events) == 1
assert events[0]["action"] == "CREATED"
assert events[0]["alert_type"] == "OFFLINE"
assert events[0]["severity"] == "CRITICAL"

print("STEP 2 PASSED: Alert created")

# STEP 3: Verifikasi database
with sqlite3.connect(TEST_DB) as connection:

    monitoring = connection.execute("""
        SELECT device_name, ip_address, status,
               latency_ms, packet_loss
        FROM monitoring_history
    """).fetchall()

    alerts = connection.execute("""
        SELECT device_name, ip_address,
               alert_type, severity, status
        FROM alert_history
    """).fetchall()

assert len(monitoring) == 1
assert len(alerts) == 1

assert monitoring[0][2] == "OFFLINE"
assert monitoring[0][4] == 100

assert alerts[0][2] == "OFFLINE"
assert alerts[0][3] == "CRITICAL"
assert alerts[0][4] == "ACTIVE"

print("STEP 3 PASSED: Database verification")

print("\n===== INTEGRATION TEST RESULT =====")
print("Monitoring records:", len(monitoring))
print("Alert records:", len(alerts))
print("Alert status:", alerts[0][4])
print("\nALL INTEGRATION TESTS PASSED")
