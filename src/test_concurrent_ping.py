import sys
import time
from pathlib import Path

from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR / "src"))

from connectivity_check import check_connectivity
from snmp_scheduler import load_inventory_devices, MAX_PING_WORKERS


def main():
    devices = load_inventory_devices()

    print("=" * 60)
    print("CONCURRENT PING TEST")
    print("=" * 60)

    start_time = time.perf_counter()

    results = []

    with ThreadPoolExecutor(max_workers=MAX_PING_WORKERS) as executor:

        future_to_device = {
            executor.submit(
                check_connectivity,
                device["ip"]
            ): device
            for device in devices
        }

        for future in as_completed(future_to_device):
            device = future_to_device[future]

            try:
                online = future.result()
                status = "ONLINE" if online else "OFFLINE"
            except Exception as error:
                status = f"ERROR: {error}"

            results.append((device["name"], device["ip"], status))

    elapsed = time.perf_counter() - start_time

    for name, ip, status in sorted(results):
        print(f"{name:<20} {ip:<16} {status}")

    online_count = sum(1 for _, _, status in results if status == "ONLINE")
    offline_count = sum(1 for _, _, status in results if status == "OFFLINE")
    error_count = sum(1 for _, _, status in results if status.startswith("ERROR"))

    print("-" * 60)
    print(f"Total perangkat : {len(devices)}")
    print(f"ONLINE          : {online_count}")
    print(f"OFFLINE         : {offline_count}")
    print(f"ERROR           : {error_count}")
    print(f"Waktu eksekusi  : {elapsed:.2f} detik")


if __name__ == "__main__":
    main()