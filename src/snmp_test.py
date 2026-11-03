
import asyncio
from getpass import getpass

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


ROUTER_IP = "192.168.16.1"
SNMP_USERNAME = "NAP"

OID_LIST = {
    "System Description": "1.3.6.1.2.1.1.1.0",
    "System Name": "1.3.6.1.2.1.1.5.0",
    "System Uptime": "1.3.6.1.2.1.1.3.0",
}


async def main():
    print("=== MikroTik SNMPv3 Test ===")

    auth_password = getpass("Authentication password: ")
    priv_password = getpass("Encryption password: ")

    snmp_engine = SnmpEngine()

    try:
        user = UsmUserData(
            SNMP_USERNAME,
            authKey=auth_password,
            privKey=priv_password,
            authProtocol=USM_AUTH_HMAC96_SHA,
            privProtocol=USM_PRIV_CFB128_AES,
        )

        target = await UdpTransportTarget.create(
            (ROUTER_IP, 161),
            timeout=3,
            retries=1,
        )

        print(f"\nConnecting to {ROUTER_IP}...\n")

        for label, oid in OID_LIST.items():
            result = await get_cmd(
                snmp_engine,
                user,
                target,
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
            )

            error_indication, error_status, error_index, var_binds = result

            if error_indication:
                print(f"[ERROR] {label}: {error_indication}")
                continue

            if error_status:
                print(
                    f"[ERROR] {label}: "
                    f"{error_status.prettyPrint()}"
                )
                continue

            for returned_oid, value in var_binds:
                print(f"[SUCCESS] {label}: {value.prettyPrint()}")

    finally:
        snmp_engine.close_dispatcher()


if __name__ == "__main__":
    asyncio.run(main())
