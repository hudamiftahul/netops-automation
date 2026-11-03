
import asyncio
import json
import getpass
from datetime import datetime
from pathlib import Path

from pysnmp.hlapi.v3arch.asyncio import (
    SnmpEngine,
    UsmUserData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    get_cmd,
    USM_AUTH_HMAC96_SHA,
    USM_PRIV_CFB128_AES,
)

from database import (
    initialize_snmp_table,
    save_snmp_metrics,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEVICES_FILE = PROJECT_DIR / "data" / "devices.json"


# SNMP OIDs: MikroTik / Host Resources MIB
OIDS = {
    "sys_name": "1.3.6.1.2.1.1.5.0",
    "uptime": "1.3.6.1.2.1.1.3.0",
    "memory_name": "1.3.6.1.2.1.25.2.3.1.3.65536",
    "memory_allocation_unit": "1.3.6.1.2.1.25.2.3.1.4.65536",
    "memory_total_units": "1.3.6.1.2.1.25.2.3.1.5.65536",
    "memory_used_units": "1.3.6.1.2.1.25.2.3.1.6.65536",
}


def load_devices():
    """Membaca inventory dan memilih perangkat MikroTik."""
    with open(DEVICES_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return [
        device for device in data["devices"]
        if device["name"] == "Router Huda"
    ]


async def get_snmp_value(
    snmp_engine,
    auth_data,
    target,
    oid
):
    """Mengambil satu nilai melalui SNMP GET."""

    error_indication, error_status, error_index, var_binds = await get_cmd(
        snmp_engine,
        auth_data,
        target,
        ContextData(),
        ObjectType(ObjectIdentity(oid)),
    )

    if error_indication:
        raise RuntimeError(str(error_indication))

    if error_status:
        raise RuntimeError(
            f"{error_status.prettyPrint()} at {error_index}"
        )

    value = var_binds[0][1]

    if value.isSameTypeWith(value.__class__()):
        if value.__class__.__name__ == "NoSuchObject":
            raise RuntimeError(f"OID tidak tersedia: {oid}")

    return value


async def collect_device(device, auth_data):
    """Mengambil dan menyimpan metrik SNMP dari satu perangkat."""

    ip_address = device["ip"]
    snmp_engine = SnmpEngine()

    try:
        target = await UdpTransportTarget.create(
            (ip_address, 161),
            timeout=3,
            retries=1,
        )

        print(f"\nCollecting: {device['name']} ({ip_address})")

        values = {}

        for metric, oid in OIDS.items():
            values[metric] = await get_snmp_value(
                snmp_engine,
                auth_data,
                target,
                oid,
            )

        # Mengolah informasi dasar
        sys_name = str(values["sys_name"])
        uptime_ticks = int(values["uptime"])

        # Mengolah informasi RAM
        memory_name = str(values["memory_name"])
        allocation_unit = int(values["memory_allocation_unit"])
        total_units = int(values["memory_total_units"])
        used_units = int(values["memory_used_units"])

        if memory_name != "main memory":
            raise ValueError(
                f"Unexpected memory type: {memory_name}"
            )

        if allocation_unit <= 0 or total_units <= 0:
            raise ValueError("Invalid memory allocation or total units")

        if used_units < 0 or used_units > total_units:
            raise ValueError("Invalid memory used units")

        memory_total = total_units * allocation_unit
        memory_used = used_units * allocation_unit
        memory_free = memory_total - memory_used

        memory_usage_percent = (
            used_units / total_units
        ) * 100

        # CPU belum tersedia
        cpu_usage = None

        checked_at = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )

        # Simpan hasil ke SQLite
        save_snmp_metrics(
            checked_at=checked_at,
            device_name=device["name"],
            ip_address=ip_address,
            sys_name=sys_name,
            uptime_ticks=uptime_ticks,
            cpu_usage=cpu_usage,
            memory_total=memory_total,
            memory_free=memory_free,
            memory_used=memory_used,
            memory_usage_percent=memory_usage_percent,
        )

        # Tampilkan hasil
        print(f"[SUCCESS] Device     : {device['name']}")
        print(f"[SUCCESS] System     : {sys_name}")
        print(f"[SUCCESS] Uptime     : {uptime_ticks} ticks")
        print(f"[SUCCESS] RAM Total  : {memory_total / 1024 / 1024:.2f} MiB")
        print(f"[SUCCESS] RAM Used   : {memory_used / 1024 / 1024:.2f} MiB")
        print(f"[SUCCESS] RAM Free   : {memory_free / 1024 / 1024:.2f} MiB")
        print(f"[SUCCESS] RAM Usage  : {memory_usage_percent:.2f}%")
        print("[INFO] CPU Usage     : Not available")

    except Exception as error:
        print(f"[ERROR] {device['name']}: {error}")

    finally:
        snmp_engine.close_dispatcher()


async def main():
    print("=== NetOps SNMP Collector ===")

    devices = load_devices()

    if not devices:
        print("[ERROR] Router Huda tidak ditemukan di devices.json")
        return

    auth_password = getpass.getpass("Authentication password: ")
    priv_password = getpass.getpass("Encryption password: ")

    auth_data = UsmUserData(
        userName="NAP",
        authKey=auth_password,
        privKey=priv_password,
        authProtocol=USM_AUTH_HMAC96_SHA,
        privProtocol=USM_PRIV_CFB128_AES,
    )

    initialize_snmp_table()

    for device in devices:
        await collect_device(device, auth_data)


if __name__ == "__main__":
    asyncio.run(main())
