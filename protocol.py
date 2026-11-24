"""Funzioni pure per il protocollo AAP delle AirPods."""

PSM = 0x1001
HEADER = bytes.fromhex("04000400")
HANDSHAKE = bytes.fromhex("00000400010002000000000000000000")
FEATURES = bytes.fromhex("040004004d00d700000000000000")
NOTIFICATIONS = bytes.fromhex("040004000f00ffffffff")
MODES = {"off": 1, "anc": 2, "transparency": 3, "adaptive": 4}
MAX_PACKET = 1024
# Impostazione 0x34 "consenti Spento" = attiva: senza, le cuffie ignorano la modalità Spento.
ALLOW_OFF = bytes.fromhex("0400040009003401000000")

_COMPONENTS = {0x04: "left", 0x02: "right", 0x08: "case"}
_STATES = {0x01: True, 0x02: False, 0x04: None, 0x00: None}


def parse(data: bytes) -> dict | None:
    """Parsa un pacchetto AAP; restituisce dict o None senza mai sollevare eccezioni."""
    try:
        if not isinstance(data, (bytes, bytearray)):
            return None
        data = bytes(data)
        if len(data) < 4 or data[:4] != HEADER:
            return None
        if data[4:6] == b"\x04\x00":
            return _parse_battery(data)
        if data[4:7] == b"\x09\x00\x0d":
            return _parse_mode(data)
        return None
    except Exception:
        return None


def _parse_battery(data: bytes) -> dict | None:
    """Parsa il pacchetto batteria (HEADER + 04 00 + [n] + blocchi da 5 byte)."""
    try:
        if len(data) < 7:
            return None
        n = data[6]
        if n not in (1, 2, 3):
            return None
        if len(data) != 7 + 5 * n:
            return None
        battery = {}
        seen = set()
        for i in range(n):
            off = 7 + 5 * i
            comp, _, level, state, _ = data[off:off + 5]
            if comp not in _COMPONENTS:
                return None
            if comp in seen:
                return None
            if state not in _STATES:
                return None
            seen.add(comp)
            name = _COMPONENTS[comp]
            if state == 0x04:
                battery[name] = {"level": None, "charging": None}
                continue
            if level > 100:
                return None
            charging = _STATES[state]
            battery[name] = {"level": level, "charging": charging}
        return {"battery": battery}
    except Exception:
        return None


def _parse_mode(data: bytes) -> dict | None:
    """Parsa il pacchetto modalità (HEADER + 09 00 0D + [m] + 00 00 00)."""
    try:
        if len(data) != 11:
            return None
        m = data[7]
        if data[8:11] != b"\x00\x00\x00":
            return None
        for name, value in MODES.items():
            if value == m:
                return {"mode": name}
        return None
    except Exception:
        return None


def mode_packet(name: str) -> bytes:
    """Costruisce il pacchetto AAP per una modalità (lancia ValueError se sconosciuta)."""
    if name not in MODES:
        raise ValueError(f"modalità sconosciuta: {name!r}")
    return HEADER + b"\x09\x00\x0d" + bytes([MODES[name]]) + b"\x00\x00\x00"
