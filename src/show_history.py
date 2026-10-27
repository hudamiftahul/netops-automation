
from database import initialize_database, get_recent_history


def main():
    initialize_database()
    history = get_recent_history(10)

    print("=" * 85)
    print("       RECENT MONITORING HISTORY")
    print("=" * 85)

    if not history:
        print("Belum ada riwayat monitoring.")
        return

    for checked_at, name, ip, status in history:
        print(
            f"{checked_at} | "
            f"{name:<18} | "
            f"{ip:<15} | "
            f"{status}"
        )

    print("=" * 85)
    print(f"Menampilkan {len(history)} catatan terbaru.")


if __name__ == "__main__":
    main()
