#!/usr/bin/env python3
"""Servizio per le AirPods Pro 3: stato batteria/modalità e comando di controllo."""

import argparse
import json
import os
import select
import signal
import socket
import sys
import tempfile
import time
from pathlib import Path

import protocol
import bluez

ALLOWED = ("anc", "transparency", "adaptive", "off")


def runtime_dir() -> Path:
    """Restituisce la cartella di runtime; solleva SystemExit se manca/non è assoluta."""
    base = os.environ.get("XDG_RUNTIME_DIR")
    if not base or not Path(base).is_absolute():
        raise SystemExit("XDG_RUNTIME_DIR mancante")
    return Path(base) / "airpods"


def empty_state() -> dict:
    """Restituisce lo stato vuoto iniziale."""
    return {"connected": False, "mode": None, "battery": {}}


def apply(state: dict, data: bytes) -> bool:
    """Applica un pacchetto allo stato; restituisce True solo se lo stato è cambiato."""
    parsed = protocol.parse(data)
    if parsed is None:
        return False
    changed = False
    if "battery" in parsed:
        new_battery = dict(state.get("battery") or {})
        for comp, values in parsed["battery"].items():
            if new_battery.get(comp) != values:
                new_battery[comp] = values
                changed = True
        if changed:
            state["battery"] = new_battery
    if "mode" in parsed:
        if state.get("mode") != parsed["mode"]:
            state["mode"] = parsed["mode"]
            changed = True
    return changed


def write_status(folder: Path, state: dict) -> None:
    """Scrive status.json in modo atomico con permessi 0600 (senza modificare state)."""
    payload = dict(state)
    payload["updated"] = int(time.time())
    folder = Path(folder)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".status-")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, folder / "status.json")
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def command(data: bytes) -> bytes | None:
    """Decodifica il comando di controllo; restituisce il pacchetto o None."""
    try:
        text = data.decode("ascii").strip()
    except Exception:
        return None
    if text not in ALLOWED:
        return None
    try:
        return protocol.mode_packet(text)
    except Exception:
        return None


def connect(address: str) -> socket.socket:
    """Apre il socket L2CAP verso le AirPods e esegue il handshake."""
    sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
    try:
        sock.settimeout(5)
        sock.connect((address, protocol.PSM))
        sock.send(protocol.HANDSHAKE)
        time.sleep(0.3)
        sock.send(protocol.FEATURES)
        time.sleep(0.3)
        sock.send(protocol.NOTIFICATIONS)
    except Exception:
        sock.close()
        raise
    sock.settimeout(None)
    return sock


def send_mode(name: str) -> int:
    """Invia il comando di modalità al servizio; restituisce 0, 1 o 2."""
    if name not in ALLOWED:
        return 2
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            sock.sendto(name.encode("ascii"), str(runtime_dir() / "ctl"))
        finally:
            sock.close()
        return 0
    except OSError:
        return 1


def serve() -> None:
    """Avvia il servizio in ciclo infinito."""
    os.umask(0o077)
    folder = runtime_dir()
    folder.mkdir(mode=0o700, parents=False, exist_ok=True)
    os.chmod(folder, 0o700)

    ctl = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        (folder / "ctl").unlink(missing_ok=True)
        ctl.bind(str(folder / "ctl"))
    except Exception:
        ctl.close()
        raise

    def _stop(sig, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _stop)

    link = None
    delay = 5
    next_try = 0
    fresh = False
    state = empty_state()
    write_status(folder, state)

    try:
        while True:
            if link is None and time.monotonic() >= next_try:
                try:
                    address = bluez.find_airpods()
                except Exception:
                    address = None
                if address:
                    try:
                        link = connect(address)
                        fresh = True
                        state["connected"] = True
                        write_status(folder, state)
                        print("AirPods collegate", file=sys.stderr)
                    except OSError:
                        next_try = time.monotonic() + delay
                        delay = min(delay * 2, 60)
                else:
                    next_try = time.monotonic() + 5

            readable = [ctl]
            if link is not None:
                readable.append(link)
            ready, _, _ = select.select(readable, [], [], 5)

            for s in ready:
                if s is ctl:
                    try:
                        msg = ctl.recv(64)
                    except OSError:
                        continue
                    packet = command(msg)
                    if packet and link is not None:
                        try:
                            link.send(packet)
                        except OSError:
                            try:
                                link.close()
                            except Exception:
                                pass
                            link = None
                            state = empty_state()
                            write_status(folder, state)
                            next_try = time.monotonic() + delay
                            delay = min(delay * 2, 60)
                            print("AirPods scollegate", file=sys.stderr)
                elif s is link:  # il link può essere stato chiuso dal comando qui sopra
                    try:
                        data = link.recv(protocol.MAX_PACKET)
                    except OSError:
                        data = b""
                    if data == b"":
                        try:
                            link.close()
                        except Exception:
                            pass
                        link = None
                        state = empty_state()
                        write_status(folder, state)
                        next_try = time.monotonic() + delay
                        delay = min(delay * 2, 60)
                        print("AirPods scollegate", file=sys.stderr)
                    else:
                        if apply(state, data):
                            write_status(folder, state)
                            if fresh:
                                delay = 5
                                fresh = False

    finally:
        for s in (ctl, link):
            try:
                if s is not None:
                    s.close()
            except Exception:
                pass
        for name in ("status.json", "ctl"):
            try:
                (folder / name).unlink(missing_ok=True)
            except Exception:
                pass


def main(argv=None) -> int:
    """Punto di ingresso: sottocomandi run e set."""
    parser = argparse.ArgumentParser(description="Servizio per le AirPods Pro 3")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run", help="avvia il servizio")
    p_set = sub.add_parser("set", help="cambia modalità")
    p_set.add_argument("mode")
    args = parser.parse_args(argv)
    if args.cmd == "run":
        serve()
        return 0
    return send_mode(args.mode)


if __name__ == "__main__":
    sys.exit(main())
