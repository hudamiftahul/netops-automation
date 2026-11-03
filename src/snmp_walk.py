
import asyncio
import getpass

from pysnmp.hlapi.v3arch.asyncio import (
    SnmpEngine,
    UsmUserData,
    UdpTransportTarget,
    ContextData,
    ObjectType,
    ObjectIdentity,
    walk_cmd,
    USM_AUTH_HMAC96_SHA,
    USM_PRIV_CFB128_AES,
)


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

    base_oid = "1.3.6.1.4.1.14988"

    print(f"\n=== SNMP WALK: {base_oid} ===")

    count = 0

    async for error_indication, error_status, error_index, var_binds in walk_cmd(
        engine,
        auth_data,
        target,
        ContextData(),
        ObjectType(ObjectIdentity(base_oid)),
        lexicographicMode=False,
    ):
        if error_indication:
            print(f"[ERROR] {error_indication}")
            break

        if error_status:
            print(f"[ERROR] {error_status.prettyPrint()}")
            break

        for oid, value in var_binds:
            print(f"{oid.prettyPrint()} = {value.prettyPrint()}")
            count += 1

        if count >= 100:
            print("\n[INFO] Output dibatasi sampai 100 objek.")
            break

    print(f"\nTotal objek ditampilkan: {count}")


if __name__ == "__main__":
    asyncio.run(main())
