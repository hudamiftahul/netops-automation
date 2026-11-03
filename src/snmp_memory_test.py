
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
    "allocation_unit": "1.3.6.1.2.1.25.2.3.1.4.65536",
    "total_units": "1.3.6.1.2.1.25.2.3.1.5.65536",
    "used_units": "1.3.6.1.2.1.25.2.3.1.6.65536",
    "memory_name": "1.3.6.1.2.1.25.2.3.1.3.65536",
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

    values = {}

    for name, oid in OIDS.items():
        error_indication, error_status, error_index, var_binds = await get_cmd(
            engine,
            auth_data,
            target,
            ContextData(),
            ObjectType(ObjectIdentity(oid)),
        )

        if error_indication or error_status:
            print(f"[ERROR] {name}: {error_indication or error_status}")
            return

        value = var_binds[0][1]
        values[name] = value

        print(f"{name}: {value.prettyPrint()}")

    allocation = int(values["allocation_unit"])
    total = int(values["total_units"])
    used = int(values["used_units"])

    free = total - used

    print("\n=== MEMORY CALCULATION ===")
    print(f"Total RAM : {total * allocation / 1024 / 1024:.2f} MiB")
    print(f"Used RAM  : {used * allocation / 1024 / 1024:.2f} MiB")
    print(f"Free RAM  : {free * allocation / 1024 / 1024:.2f} MiB")
    print(f"Usage     : {used / total * 100:.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
