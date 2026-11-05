
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

from database import initialize_database, save_result

PROJECT_DIR = Path(__file__).resolve().parents[1]
INVENTORY_FILE = PROJECT_DIR / "data" / "devices.json"

PING_COUNT = 4
PING_TIMEOUT_MS = 1000


def measure_connectivity(ip):
    """
    Mengukur status koneksi, rata-rata latency, dan packet loss.
    Menggunakan 4 paket ICMP untuk setiap perangkat.
    """
    try:
        result = subprocess.run(
            [
                "ping",
                "-n", str(PING_COUNT),
                "-w", str(PING_TIMEOUT_MS),
                ip
            ],
            capture_output=True,
            text=True,
            timeout=7,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        output = result.stdout + result.stderr

        latency_samples = []
        received_count = 0

        for line in output.splitlines():

            # Mendeteksi balasan ping Windows dalam bahasa Inggris
            # maupun Indonesia.
            is_reply = bool(
                re.search(r"\bTTL\s*[=:]", line, re.IGNORECASE)
            )

            latency_match = re.search(
                r"\b(?:time|waktu)\s*([=<])\s*"
                r"(\d+(?:[.,]\d+)?)\s*"
                r"(?:ms|msec|md)?",
                line,
                re.IGNORECASE
            )

            if latency_match:
                is_reply = True

                operator = latency_match.group(1)
                latency = float(
                    latency_match.group(2).replace(",", ".")
                )

                # Contoh: time<1ms dianggap sekitar 0.5 ms.
                if operator == "<":
                    latency = latency / 2

                latency_samples.append(latency)

            if is_reply:
                received_count += 1

        # Batasi jumlah balasan agar tidak melebihi paket yang dikirim.
        received_count = min(received_count, PING_COUNT)

        packet_loss = (
            (PING_COUNT - received_count) / PING_COUNT
        ) * 100

        latency_ms = None

        if latency_samples:
            latency_ms = round(
                sum(latency_samples) / len(latency_samples),
                2
            )

        status = "ONLINE" if received_count > 0 else "OFFLINE"

        return {
            "status": status,
            "latency_ms": latency_ms,
            "packet_loss": round(packet_loss, 2)
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "OFFLINE",
            "latency_ms": None,
            "packet_loss": 100.0
        }


def check_connectivity(ip):
    """Memeriksa konektivitas tanpa membuka jendela terminal."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW
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
