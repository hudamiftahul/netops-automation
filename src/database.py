
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
