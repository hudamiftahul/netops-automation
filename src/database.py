
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
