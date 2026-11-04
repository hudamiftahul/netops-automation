
import asyncio
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
    initialize_snmp_table,
    initialize_scheduler_health,
    update_scheduler_health,
)
from snmp_collector import load_devices, collect_device


# Project configuration
PROJECT_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = PROJECT_DIR / "data"
LOG_FILE = LOG_DIR / "snmp_scheduler.log"

INTERVAL_SECONDS = 300
SERVICE_NAME = "NetOpsAutomation"


# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)


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

logger = logging.getLogger("SNMP-Scheduler")

def get_current_time():
    return datetime.now().astimezone().isoformat(timespec="seconds")


async def run_scheduler(auth_data):
    devices = load_devices()

    if not devices:
        logger.error("Tidak ada perangkat untuk dimonitor.")
        return

    initialize_snmp_table()
    initialize_scheduler_health()

    logger.info("========================================")
    logger.info("SNMP Scheduler started.")
    logger.info("Total devices: %s", len(devices))
    logger.info("Polling interval: %s seconds", INTERVAL_SECONDS)

    cycle = 0

    while True:
        cycle += 1
        cycle_failures = 0

        cycle_started_at = get_current_time()

        logger.info("Polling cycle #%s started.", cycle)

        update_scheduler_health(
            status="RUNNING",
            cycle=cycle,
            failed_devices=0,
            message="Polling sedang berjalan",
            started_at=cycle_started_at,
        )

        for device in devices:
            device_name = device.get("name", "Unknown")
            device_ip = device.get("ip", "Unknown")

            try:
                await collect_device(device, auth_data)

                logger.info(
                    "Polling completed | Device: %s | IP: %s",
                    device_name,
                    device_ip,
                )

            except Exception:
                cycle_failures += 1

                logger.exception(
                    "Polling failed | Device: %s | IP: %s",
                    device_name,
                    device_ip,
                )

        cycle_completed_at = get_current_time()

        if cycle_failures > 0:
            scheduler_status = "DEGRADED"
            message = (
                f"{cycle_failures} perangkat gagal dipolling"
            )
        else:
            scheduler_status = "OK"
            message = "Semua proses polling selesai"

        update_scheduler_health(
            status=scheduler_status,
            cycle=cycle,
            failed_devices=cycle_failures,
            message=message,
            completed_at=cycle_completed_at,
        )

        logger.info(
            "Polling cycle #%s finished. Status: %s. "
            "Failed devices: %s",
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
    logger.info("Loading SNMP credentials from Windows Credential Manager.")

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
        logger.info("SNMP Scheduler stopped by user.")

    except Exception:
        logger.exception("SNMP Scheduler terminated unexpectedly.")
