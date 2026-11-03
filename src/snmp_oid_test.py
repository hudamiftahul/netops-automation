
import asyncio
import getpass

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


OIDS = {
    "sys_name": "1.3.6.1.2.1.1.5.0",
    "uptime": "1.3.6.1.2.1.1.3.0",
    "cpu": "1.3.6.1.4.1.14988.1.1.3.10.0",
    "memory_total": "1.3.6.1.4.1.14988.1.1.3.1.0",
    "memory_free": "1.3.6.1.4.1.14988.1.1.3.2.0",
}


async def main():
    auth_password = getpass.getpass("Authentication password: ")
    priv_password = getpass.getpass("Encryption password: ")

    auth_data = UsmUserData(
        userName="NAP",
        authKey=auth_password,
        privKey=priv_password,
        authProtocol=USM_AUTH_HMAC96_SHA,
        privProtocol=USM_PRIV_CFB128_AES,
    )

    engine = SnmpEngine()

    target = await UdpTransportTarget.create(
        ("192.168.16.1", 161),
        timeout=3,
        retries=1,
    )

    print("\n=== SNMP OID Diagnostic ===")

    for name, oid in OIDS.items():
        try:
            error_indication, error_status, error_index, var_binds = await get_cmd(
                engine,
                auth_data,
                target,
                ContextData(),
                ObjectType(ObjectIdentity(oid)),
            )

            print(f"\n{name} | OID: {oid}")

            if error_indication:
                print(f"ERROR: {error_indication}")
            elif error_status:
                print(f"ERROR: {error_status.prettyPrint()}")
            else:
                for returned_oid, value in var_binds:
                    print(f"Type  : {type(value).__name__}")
                    print(f"Value : {value!r}")
                    print(f"Pretty: {value.prettyPrint()}")

        except Exception as exc:
            print(f"\n{name} | EXCEPTION: {exc}")

    print("\n=== Diagnostic selesai ===")


if __name__ == "__main__":
    asyncio.run(main())
