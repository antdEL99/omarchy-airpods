"""Trova l'indirizzo Bluetooth delle AirPods collegate via bluetoothctl."""

import re
import subprocess

AAP_UUID = "74ec2172-0bad-4d01-8f77-997b2be0722a"

_DEV_RE = re.compile(r"^Device\s+([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})(?:\s+(.*))?$")


def run(args: list[str]) -> str:
    """Esegue bluetoothctl con args e restituisce stdout ("" in caso di errore)."""
    try:
        proc = subprocess.run(
            ["bluetoothctl", *args],
            capture_output=True,
            text=True,
            timeout=5,
            stdin=subprocess.DEVNULL,
        )
        if proc.returncode != 0:
            return ""
        return proc.stdout
    except Exception:
        return ""


def parse_devices(text: str) -> list[str]:
    """Restituisce gli indirizzi dalle righe 'Device <addr> ...', in maiuscolo."""
    result = []
    for line in text.splitlines():
        m = _DEV_RE.match(line.strip())
        if m:
            result.append(m.group(1).upper())
    return result


def is_airpods(info: str) -> bool:
    """True se l'output di info indica AirPods connesse e accoppiate."""
    paired = False
    connected = False
    uuid = False
    for line in info.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("name:") or stripped.lower().startswith("alias:"):
            continue
        if re.fullmatch(r"Paired:\s*yes", stripped, re.IGNORECASE):
            paired = True
        elif re.fullmatch(r"Connected:\s*yes", stripped, re.IGNORECASE):
            connected = True
        elif stripped.lower().startswith("uuid:") and AAP_UUID in stripped.lower():
            uuid = True
    return paired and connected and uuid


def find_airpods(run=run) -> str | None:
    """Restituisce l'indirizzo se esattamente un dispositivo è AirPods, altrimenti None."""
    found = []
    for addr in parse_devices(run(["devices", "Connected"])):
        if is_airpods(run(["info", addr])):
            found.append(addr)
    return found[0] if len(found) == 1 else None
