
import sqlite3
from contextlib import closing
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_DIR / "data" / "netops.db"

LATENCY_WARNING_THRESHOLD = 200
PACKET_LOSS_WARNING_THRESHOLD = 20


def get_alert_connection(db_path=DATABASE_FILE):
    """Membuka koneksi database alert."""
    return sqlite3.connect(db_path, timeout=10)


def initialize_alert_table(db_path=DATABASE_FILE):
    """Membuat tabel dan index alert jika belum tersedia."""
    with closing(get_alert_connection(db_path)) as connection:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_name TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL
                        CHECK (severity IN ('WARNING', 'CRITICAL')),
                    message TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    status TEXT NOT NULL
                        CHECK (status IN ('ACTIVE', 'RESOLVED')),
                    resolved_at TEXT
                )
            """)

            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_active
                ON alert_history (ip_address, alert_type, status)
            """)

            connection.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_alert_unique_active
                ON alert_history (ip_address, alert_type)
                WHERE status = 'ACTIVE'
            """)


def raise_or_update_alert(
    connection,
    checked_at,
    device_name,
    ip_address,
    alert_type,
    severity,
    message,
):
    """Membuat alert baru atau memperbarui alert aktif."""

    existing = connection.execute("""
        SELECT id
        FROM alert_history
        WHERE ip_address = ?
          AND alert_type = ?
          AND status = 'ACTIVE'
        LIMIT 1
    """, (ip_address, alert_type)).fetchone()

    if existing:
        alert_id = existing[0]

        connection.execute("""
            UPDATE alert_history
            SET device_name = ?,
                severity = ?,
                message = ?,
                last_seen = ?
            WHERE id = ?
        """, (
            device_name,
            severity,
            message,
            checked_at,
            alert_id,
        ))

        return {
            "action": "UPDATED",
            "alert_id": alert_id,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
        }

    cursor = connection.execute("""
        INSERT INTO alert_history (
            device_name,
            ip_address,
            alert_type,
            severity,
            message,
            first_seen,
            last_seen,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
    """, (
        device_name,
        ip_address,
        alert_type,
        severity,
        message,
        checked_at,
        checked_at,
    ))

    return {
        "action": "CREATED",
        "alert_id": cursor.lastrowid,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
    }


def resolve_alert(connection, checked_at, ip_address, alert_type):
    """Menyelesaikan alert aktif dan mengembalikan event."""

    rows = connection.execute("""
        SELECT id, severity, message
        FROM alert_history
        WHERE ip_address = ?
          AND alert_type = ?
          AND status = 'ACTIVE'
    """, (ip_address, alert_type)).fetchall()

    if not rows:
        return []

    connection.execute("""
        UPDATE alert_history
        SET status = 'RESOLVED',
            resolved_at = ?
        WHERE ip_address = ?
          AND alert_type = ?
          AND status = 'ACTIVE'
    """, (
        checked_at,
        ip_address,
        alert_type,
    ))

    return [
        {
            "action": "RESOLVED",
            "alert_id": row[0],
            "alert_type": alert_type,
            "severity": row[1],
            "message": row[2],
        }
        for row in rows
    ]


def evaluate_connectivity_alert(
    checked_at,
    device_name,
    ip_address,
    status,
    latency_ms,
    packet_loss,
    db_path=DATABASE_FILE,
):
    """
    Mengevaluasi kondisi konektivitas perangkat.

    OFFLINE:
        CRITICAL

    Latency >= 200 ms:
        WARNING

    Packet loss >= 20%:
        WARNING

    Mengembalikan daftar event:
        CREATED, UPDATED, RESOLVED.
    """

    status = status.upper()

    if status not in ("ONLINE", "OFFLINE"):
        raise ValueError(f"Invalid connectivity status: {status}")

    events = []

    with closing(get_alert_connection(db_path)) as connection:
        with connection:

            # PRIORITAS 1: DEVICE OFFLINE
            if status == "OFFLINE":

                events.append(
                    raise_or_update_alert(
                        connection,
                        checked_at,
                        device_name,
                        ip_address,
                        "OFFLINE",
                        "CRITICAL",
                        f"Device {device_name} ({ip_address}) is offline.",
                    )
                )

                events.extend(
                    resolve_alert(
                        connection,
                        checked_at,
                        ip_address,
                        "HIGH_LATENCY",
                    )
                )

                events.extend(
                    resolve_alert(
                        connection,
                        checked_at,
                        ip_address,
                        "PACKET_LOSS",
                    )
                )

                return events

            # DEVICE SUDAH ONLINE
            events.extend(
                resolve_alert(
                    connection,
                    checked_at,
                    ip_address,
                    "OFFLINE",
                )
            )

            # PRIORITAS 2: HIGH LATENCY
            if latency_ms is not None:

                if latency_ms >= LATENCY_WARNING_THRESHOLD:

                    events.append(
                        raise_or_update_alert(
                            connection,
                            checked_at,
                            device_name,
                            ip_address,
                            "HIGH_LATENCY",
                            "WARNING",
                            f"High latency detected: {latency_ms:.2f} ms",
                        )
                    )

                else:
                    events.extend(
                        resolve_alert(
                            connection,
                            checked_at,
                            ip_address,
                            "HIGH_LATENCY",
                        )
                    )

            # PRIORITAS 3: PACKET LOSS
            if packet_loss is not None:

                if packet_loss >= PACKET_LOSS_WARNING_THRESHOLD:

                    events.append(
                        raise_or_update_alert(
                            connection,
                            checked_at,
                            device_name,
                            ip_address,
                            "PACKET_LOSS",
                            "WARNING",
                            f"High packet loss detected: {packet_loss:.2f}%",
                        )
                    )

                else:
                    events.extend(
                        resolve_alert(
                            connection,
                            checked_at,
                            ip_address,
                            "PACKET_LOSS",
                        )
                    )

    return events
