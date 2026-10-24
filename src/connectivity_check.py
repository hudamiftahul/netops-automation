
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Menentukan lokasi file inventory
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

    print("=" * 55)
    print("       NETOPS AUTOMATION PLATFORM")
    print("       Connectivity Monitoring")
    print("=" * 55)
    print(f"Waktu pemeriksaan: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("-" * 55)

    for device in inventory["devices"]:
        ip = device["ip"]
        name = device["name"]

        is_online = check_connectivity(ip)
        status = "ONLINE" if is_online else "OFFLINE"

        print(f"{name:<20} {ip:<16} {status}")

    print("-" * 55)


if __name__ == "__main__":
    main()
