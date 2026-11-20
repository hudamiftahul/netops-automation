
import tempfile
from pathlib import Path

from alert_engine import (
    initialize_alert_table,
    evaluate_connectivity_alert,
)

TEST_DB = Path(tempfile.gettempdir()) / "netops_alert_events_test.db"

if TEST_DB.exists():
    TEST_DB.unlink()

initialize_alert_table(TEST_DB)


def evaluate(status, latency=None, packet_loss=None, minute="00"):
    return evaluate_connectivity_alert(
        checked_at=f"2026-11-20T10:{minute}:00",
        device_name="Router Event Test",
        ip_address="192.0.2.10",
        status=status,
        latency_ms=latency,
        packet_loss=packet_loss,
        db_path=TEST_DB,
    )


# TEST 1: Alert OFFLINE baru dibuat
events = evaluate("OFFLINE", minute="00")

assert len(events) == 1
assert events[0]["action"] == "CREATED"
assert events[0]["alert_type"] == "OFFLINE"
assert events[0]["severity"] == "CRITICAL"

print("TEST 1 PASSED: OFFLINE CREATED")


# TEST 2: OFFLINE berulang hanya memperbarui alert
events = evaluate("OFFLINE", minute="05")

assert len(events) == 1
assert events[0]["action"] == "UPDATED"
assert events[0]["alert_type"] == "OFFLINE"

print("TEST 2 PASSED: OFFLINE UPDATED")


# TEST 3: ONLINE menyelesaikan alert OFFLINE
events = evaluate("ONLINE", 10, 0, minute="10")

assert len(events) == 1
assert events[0]["action"] == "RESOLVED"
assert events[0]["alert_type"] == "OFFLINE"

print("TEST 3 PASSED: OFFLINE RESOLVED")


# TEST 4: Latency tinggi membuat alert baru
events = evaluate("ONLINE", 250, 0, minute="15")

assert len(events) == 1
assert events[0]["action"] == "CREATED"
assert events[0]["alert_type"] == "HIGH_LATENCY"

print("TEST 4 PASSED: HIGH_LATENCY CREATED")


# TEST 5: Latency tinggi berulang memperbarui alert
events = evaluate("ONLINE", 270, 0, minute="20")

assert len(events) == 1
assert events[0]["action"] == "UPDATED"

print("TEST 5 PASSED: HIGH_LATENCY UPDATED")


# TEST 6: Latency normal menyelesaikan alert
events = evaluate("ONLINE", 20, 0, minute="25")

assert len(events) == 1
assert events[0]["action"] == "RESOLVED"

print("TEST 6 PASSED: HIGH_LATENCY RESOLVED")


# TEST 7: Packet loss tinggi membuat alert baru
events = evaluate("ONLINE", 20, 30, minute="30")

assert len(events) == 1
assert events[0]["action"] == "CREATED"
assert events[0]["alert_type"] == "PACKET_LOSS"

print("TEST 7 PASSED: PACKET_LOSS CREATED")


# TEST 8: OFFLINE menyelesaikan packet loss
events = evaluate("OFFLINE", minute="35")

assert len(events) == 2
assert events[0]["action"] == "CREATED"
assert events[0]["alert_type"] == "OFFLINE"

resolved_events = [
    event for event in events
    if event["action"] == "RESOLVED"
]

assert len(resolved_events) == 1
assert resolved_events[0]["alert_type"] == "PACKET_LOSS"

print("TEST 8 PASSED: OFFLINE CREATED + PACKET_LOSS RESOLVED")


# TEST 9: Periksa tidak ada alert aktif setelah pemulihan
events = evaluate("ONLINE", 10, 0, minute="40")

assert len(events) == 1
assert events[0]["action"] == "RESOLVED"
assert events[0]["alert_type"] == "OFFLINE"

print("TEST 9 PASSED: OFFLINE RESOLVED")


print("\nALL EVENT TESTS PASSED")
