"""Test unitari per airpodsd (senza Bluetooth reale)."""

import json
import os
import stat
import sys
import tempfile
import socket
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import airpodsd
import protocol

BATTERY_HEX = "04000400040003020164020104016301010801110201"


class AirPodsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "airpods"
        self.env = mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": self.tmp.name})
        self.env.start()
        self.addCleanup(self.env.stop)

    # ---- apply ----

    def test_apply_mode_packet(self):
        state = airpodsd.empty_state()
        data = protocol.mode_packet("anc")
        self.assertTrue(airpodsd.apply(state, data))
        self.assertEqual(state["mode"], "anc")
        # secondo apply con lo stesso pacchetto: nessuna modifica
        self.assertFalse(airpodsd.apply(state, data))

    def test_apply_battery_hex_packet(self):
        state = airpodsd.empty_state()
        data = bytes.fromhex(BATTERY_HEX)
        parsed = protocol.parse(data)
        self.assertIsNotNone(parsed)
        self.assertIn("battery", parsed)
        self.assertTrue(airpodsd.apply(state, data))
        self.assertEqual(state["battery"], parsed["battery"])
        self.assertFalse(airpodsd.apply(state, data))

    def test_apply_invalid_packet(self):
        state = airpodsd.empty_state()
        snapshot = dict(state)
        snapshot["battery"] = {}
        self.assertFalse(airpodsd.apply(state, b"\x00\x01\x02"))
        self.assertEqual(state, snapshot)

    def test_apply_partial_battery(self):
        state = airpodsd.empty_state()
        state["battery"] = {"left": {"level": 80, "charging": False},
                           "right": {"level": 70, "charging": False}}
        # pacchetto con solo il case: HEADER + 04 00 + n=1 + blocco da 5 byte
        block = bytes([0x08, 0x00, 50, 0x01, 0x00])
        data = protocol.HEADER + b"\x04\x00" + b"\x01" + block
        self.assertTrue(airpodsd.apply(state, data))
        self.assertEqual(state["battery"]["left"], {"level": 80, "charging": False})
        self.assertEqual(state["battery"]["right"], {"level": 70, "charging": False})
        self.assertEqual(state["battery"]["case"], {"level": 50, "charging": True})

    # ---- write_status ----

    def test_write_status(self):
        self.folder.mkdir()
        state = {"connected": False, "mode": "anc", "battery": {}}
        airpodsd.write_status(self.folder, state)
        self.assertNotIn("updated", state)
        status = self.folder / "status.json"
        self.assertTrue(status.exists())
        perms = stat.S_IMODE(status.stat().st_mode)
        self.assertEqual(perms, 0o600)
        data = json.loads(status.read_text())
        self.assertEqual(data["connected"], False)
        self.assertEqual(data["mode"], "anc")
        self.assertEqual(data["battery"], {})
        self.assertIsInstance(data["updated"], int)
        leftovers = list(self.folder.glob(".status-*"))
        self.assertEqual(leftovers, [])

    # ---- command ----

    def test_command_allowed(self):
        for name in airpodsd.ALLOWED:
            self.assertEqual(airpodsd.command(name.encode("ascii")), protocol.mode_packet(name))
            self.assertEqual(airpodsd.command(("  " + name + "  ").encode("ascii")),
                             protocol.mode_packet(name))

    def test_command_rejected(self):
        self.assertIsNone(airpodsd.command(b"xyz"))
        self.assertIsNone(airpodsd.command(b""))
        self.assertIsNone(airpodsd.command(b"\xff"))
        self.assertIsNone(airpodsd.command(b"anc;rm"))

    # ---- send_mode ----

    def test_send_mode_disallowed(self):
        self.assertEqual(airpodsd.send_mode("xyz"), 2)

    def test_send_mode_no_socket(self):
        self.assertEqual(airpodsd.send_mode("anc"), 1)

    def test_send_mode_delivers(self):
        self.folder.mkdir()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.addCleanup(server.close)
        server.bind(str(self.folder / "ctl"))
        self.assertEqual(airpodsd.send_mode("anc"), 0)
        server.settimeout(2)
        msg, _ = server.recvfrom(64)
        self.assertEqual(msg, b"anc")

    # ---- runtime_dir ----

    def test_runtime_dir_relative(self):
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": "relative/path"}):
            with self.assertRaises(SystemExit):
                airpodsd.runtime_dir()

    def test_runtime_dir_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                airpodsd.runtime_dir()


if __name__ == "__main__":
    unittest.main()
