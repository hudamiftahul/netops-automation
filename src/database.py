
import sqlite3
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATABASE_FILE = PROJECT_DIR / "data" / "netops.db"


def get_connection():
    """Membuka koneksi ke database SQLite."""
    return sqlite3.connect(DATABASE_FILE)


def initialize_database():
    """Membuat tabel riwayat jika belum tersedia."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at TEXT NOT NULL,
                device_name TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                status TEXT NOT NULL
                    CHECK (status IN ('ONLINE', 'OFFLINE'))
            )
        """)


def save_result(checked_at, device_name, ip_address, status):
    """Menyimpan satu hasil monitoring."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO monitoring_history (
                checked_at,
                device_name,
                ip_address,
                status
            )
            VALUES (?, ?, ?, ?)
        """, (checked_at, device_name, ip_address, status))


def get_recent_history(limit=10):
    """Mengambil riwayat terbaru."""
    with get_connection() as connection:
        return connection.execute("""
            SELECT checked_at, device_name, ip_address, status
            FROM monitoring_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()



def initialize_snmp_table():
    """Membuat tabel khusus hasil monitoring SNMP."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS snmp_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at TEXT NOT NULL,
                device_name TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                sys_name TEXT,
                uptime_ticks INTEGER,
                cpu_usage REAL,
                memory_total INTEGER,
                memory_free INTEGER,
                memory_used INTEGER,
                memory_usage_percent REAL
            )
        """)


def save_snmp_metrics(
    checked_at,
    device_name,
    ip_address,
    sys_name,
    uptime_ticks,
    cpu_usage,
    memory_total,
    memory_free,
    memory_used,
    memory_usage_percent
):
    """Menyimpan hasil pengambilan metrik SNMP."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO snmp_history (
                checked_at,
                device_name,
                ip_address,
                sys_name,
                uptime_ticks,
                cpu_usage,
                memory_total,
                memory_free,
                memory_used,
                memory_usage_percent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            checked_at,
            device_name,
            ip_address,
            sys_name,
            uptime_ticks,
            cpu_usage,
            memory_total,
            memory_free,
            memory_used,
            memory_usage_percent
        ))


def initialize_scheduler_health():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS scheduler_health (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_started_at TEXT,
                last_completed_at TEXT,
                status TEXT NOT NULL,
                cycle INTEGER NOT NULL DEFAULT 0,
                failed_devices INTEGER NOT NULL DEFAULT 0,
                message TEXT
            )
        """)


def update_scheduler_health(
    status,
    cycle,
    failed_devices=0,
    message=None,
    started_at=None,
    completed_at=None
):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO scheduler_health (
                id,
                last_started_at,
                last_completed_at,
                status,
                cycle,
                failed_devices,
                message
            )
            VALUES (1, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(id) DO UPDATE SET
                last_started_at = COALESCE(
                    excluded.last_started_at,
                    scheduler_health.last_started_at
                ),
                last_completed_at = COALESCE(
                    excluded.last_completed_at,
                    scheduler_health.last_completed_at
                ),
                status = excluded.status,
                cycle = excluded.cycle,
                failed_devices = excluded.failed_devices,
                message = excluded.message
        """, (
            started_at,
            completed_at,
            status,
            cycle,
            failed_devices,
            message
        ))


def get_scheduler_health():
    with get_connection() as connection:
        return connection.execute("""
            SELECT
                last_started_at,
                last_completed_at,
                status,
                cycle,
                failed_devices,
                message
            FROM scheduler_health
            WHERE id = 1
        """).fetchone()

