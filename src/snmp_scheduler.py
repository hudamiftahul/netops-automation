import asyncio
import json
import logging
import keyring

from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

from pysnmp.hlapi.v3arch.asyncio import (
    UsmUserData,
    USM_AUTH_HMAC96_SHA,
    USM_PRIV_CFB128_AES,
)

from database import (
    initialize_database,
    save_result,
    initialize_snmp_table,
    initialize_scheduler_health,
    update_scheduler_health,
)

from connectivity_check import check_connectivity
from snmp_collector import load_devices, collect_device


# Project configuration
PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
INVENTORY_FILE = DATA_DIR / "devices.json"
LOG_FILE = DATA_DIR / "snmp_scheduler.log"

INTERVAL_SECONDS = 300
SERVICE_NAME = "NetOpsAutomation"


# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Logging configuration
handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=2 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[handler],
)

logger = logging.getLogger("NetOps-Scheduler")


def get_current_time():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_inventory_devices():
    """Membaca seluruh perangkat dari inventory."""
    with open(INVENTORY_FILE, "r", encoding="utf-8") as file:
        inventory = json.load(file)

    return inventory.get("devices", [])


def run_ping_monitoring():
    """Ping seluruh perangkat dan menyimpan hasilnya ke SQLite."""
    devices = load_inventory_devices()

    checked_at = get_current_time()

    online_count = 0
    offline_count = 0
    failed_checks = 0

    logger.info("Starting connectivity monitoring.")
    logger.info("Total ping devices: %s", len(devices))

    for device in devices:
        name = device.get("name", "Unknown")
        ip = device.get("ip", "Unknown")

        try:
            is_online = check_connectivity(ip)
            status = "ONLINE" if is_online else "OFFLINE"

            save_result(checked_at, name, ip, status)

            if is_online:
                online_count += 1
                logger.info(
                    "PING ONLINE | Device: %s | IP: %s",
                    name,
                    ip,
                )
            else:
                offline_count += 1
                logger.warning(
                    "PING OFFLINE | Device: %s | IP: %s",
                    name,
                    ip,
                )

        except Exception:
            failed_checks += 1
            logger.exception(
                "PING CHECK ERROR | Device: %s | IP: %s",
                name,
                ip,
            )

    logger.info(
        "Ping completed | Total: %s | Online: %s | Offline: %s | Errors: %s",
        len(devices),
        online_count,
        offline_count,
        failed_checks,
    )

    return failed_checks


async def run_scheduler(auth_data):
    # Load SNMP devices using existing collector configuration
    snmp_devices = load_devices()

    initialize_database()
    initialize_snmp_table()
    initialize_scheduler_health()

    logger.info("========================================")
    logger.info("NetOps Unified Scheduler started.")
    logger.info("SNMP devices: %s", len(snmp_devices))
    logger.info("Polling interval: %s seconds", INTERVAL_SECONDS)

    cycle = 0

    while True:
        cycle += 1
        cycle_failures = 0

        cycle_started_at = get_current_time()

        logger.info("========================================")
        logger.info("Polling cycle #%s started.", cycle)

        update_scheduler_health(
            status="RUNNING",
            cycle=cycle,
            failed_devices=0,
            message="Ping dan SNMP monitoring sedang berjalan",
            started_at=cycle_started_at,
        )

        # STEP 1: Ping all inventory devices
        try:
            ping_errors = run_ping_monitoring()
            cycle_failures += ping_errors

        except Exception:
            cycle_failures += 1
            logger.exception("Connectivity monitoring failed.")

        # STEP 2: SNMP monitoring
        logger.info("Starting SNMP monitoring.")

        for device in snmp_devices:
            device_name = device.get("name", "Unknown")
            device_ip = device.get("ip", "Unknown")

            try:
                await collect_device(device, auth_data)

                logger.info(
                    "SNMP polling completed | Device: %s | IP: %s",
                    device_name,
                    device_ip,
                )

            except Exception:
                cycle_failures += 1

                logger.exception(
                    "SNMP polling failed | Device: %s | IP: %s",
                    device_name,
                    device_ip,
                )

        # STEP 3: Update scheduler health
        cycle_completed_at = get_current_time()

        if cycle_failures > 0:
            scheduler_status = "DEGRADED"
            message = (
                f"{cycle_failures} proses monitoring mengalami error"
            )
        else:
            scheduler_status = "OK"
            message = "Ping dan SNMP monitoring selesai"

        update_scheduler_health(
            status=scheduler_status,
            cycle=cycle,
            failed_devices=cycle_failures,
            message=message,
            completed_at=cycle_completed_at,
        )

        logger.info(
            "Polling cycle #%s finished | Status: %s | Errors: %s",
            cycle,
            scheduler_status,
            cycle_failures,
        )

        logger.info(
            "Next polling in %s seconds.",
            INTERVAL_SECONDS,
        )

        await asyncio.sleep(INTERVAL_SECONDS)


async def main():
    logger.info(
        "Loading SNMP credentials from Windows Credential Manager."
    )

    auth_password = keyring.get_password(SERVICE_NAME, "NAP_AUTH")
    priv_password = keyring.get_password(SERVICE_NAME, "NAP_PRIV")

    if not auth_password or not priv_password:
        raise RuntimeError(
            "SNMP credentials tidak ditemukan. "
            "Jalankan setup_snmp_credentials.py terlebih dahulu."
        )

    auth_data = UsmUserData(
        userName="NAP",
        authKey=auth_password,
        privKey=priv_password,
        authProtocol=USM_AUTH_HMAC96_SHA,
        privProtocol=USM_PRIV_CFB128_AES,
    )

    await run_scheduler(auth_data)


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("NetOps Scheduler stopped by user.")

    except Exception:
        logger.exception("NetOps Scheduler terminated unexpectedly.")