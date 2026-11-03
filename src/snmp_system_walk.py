
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


BASE_OIDS = [
    "1.3.6.1.2.1.25",
    "1.3.6.1.4.1.14988.1.1.3",
]


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

    for base_oid in BASE_OIDS:
        print(f"\n=== WALK {base_oid} ===")
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
                print(
                    f"{oid.prettyPrint()} = "
                    f"{value.prettyPrint()} "
                    f"[{type(value).__name__}]"
                )
                count += 1

                if count >= 80:
                    print("[INFO] Output dibatasi sampai 80 objek.")
                    break

            if count >= 80:
                break

        print(f"Total objek: {count}")


if __name__ == "__main__":
    asyncio.run(main())
