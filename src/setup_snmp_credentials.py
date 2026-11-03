
import getpass
import keyring

SERVICE_NAME = "NetOpsAutomation"

print("=== SNMP Credential Setup ===")

auth_password = getpass.getpass(
    "SNMP authentication password: "
)

priv_password = getpass.getpass(
    "SNMP encryption password: "
)

if not auth_password or not priv_password:
    raise ValueError("Password tidak boleh kosong.")

keyring.set_password(
    SERVICE_NAME,
    "NAP_AUTH",
    auth_password
)

keyring.set_password(
    SERVICE_NAME,
    "NAP_PRIV",
    priv_password
)

print("[SUCCESS] SNMP credentials saved to Windows Credential Manager.")
