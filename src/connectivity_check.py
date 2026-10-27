
import json
import subprocess
from pathlib import Path
from datetime import datetime

from database import initialize_database, save_result

PROJECT_DIR = Path(__file__).resolve().parents[1]
INVENTORY_FILE = PROJECT_DIR / "data" / "devices.json"


def check_connectivity(ip):
    """Memeriksa apakah alamat IP merespons ping."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],
            capture_output=True,
            text=True,
            timeout=3
        )
        return result.returncode == 0

    except subprocess.TimeoutExpired:
        return False


def main():
    with open(INVENTORY_FILE, "r", encoding="utf-8") as file:
        inventory = json.load(file)

    initialize_database()

    checked_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    online_count = 0
    offline_count = 0

    print("=" * 60)
    print("       NETOPS AUTOMATION PLATFORM")
    print("       Connectivity Monitoring")
    print("=" * 60)
    print(f"Waktu pemeriksaan: {checked_at}")
    print("-" * 60)

    for device in inventory["devices"]:
        name = device["name"]
        ip = device["ip"]

        is_online = check_connectivity(ip)
        status = "ONLINE" if is_online else "OFFLINE"

        save_result(checked_at, name, ip, status)

        if is_online:
            online_count += 1
        else:
            offline_count += 1

        print(f"{name:<20} {ip:<16} {status}")

    print("-" * 60)
    print(f"Total perangkat : {online_count + offline_count}")
    print(f"ONLINE          : {online_count}")
    print(f"OFFLINE         : {offline_count}")
    print("Hasil monitoring tersimpan di SQLite.")


if __name__ == "__main__":
    main()
