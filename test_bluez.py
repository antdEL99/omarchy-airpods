import unittest
from unittest.mock import patch

import bluez

INFO_NO = """Device AA:BB:CC:DD:EE:FF (public)
\tName: AirPodsD. Pro
\tAlias: AirPodsD. Pro
\tClass: 0x00240418 (2360344)
\tIcon: audio-headphones
\tPaired: yes
\tBonded: yes
\tTrusted: yes
\tBlocked: no
\tConnected: no
\tLegacyPairing: no
\tCablePairing: no
\tUUID: Service Discovery Serve.. (00001000-0000-1000-8000-00805f9b34fb)
\tUUID: Audio Sink                (0000110b-0000-1000-8000-00805f9b34fb)
\tUUID: Vendor specific           (4715650b-5e9d-4ac2-b898-a4fc0aa5df78)
\tUUID: Vendor specific           (74ec2172-0bad-4d01-8f77-997b2be0722a)
\tModalias: bluetooth:v004Cp2027d242F
"""
INFO_YES = INFO_NO.replace("Connected: no", "Connected: yes")

DEVICES = """Device AA:BB:CC:DD:EE:FF AirPodsD. Pro
Device 11:22:33:44:55:66 Mouse
"""


class TestParse(unittest.TestCase):
    def test_example(self):
        self.assertEqual(
            bluez.parse_devices(DEVICES),
            ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"],
        )

    def test_empty_and_malformed(self):
        self.assertEqual(bluez.parse_devices(""), [])
        self.assertEqual(bluez.parse_devices("not a device\nDevice ZZ:XX\n\n"), [])

    def test_name_with_spaces_and_colons(self):
        self.assertEqual(
            bluez.parse_devices("Device aa:bb:cc:dd:ee:ff My: AirPods: Pro\n"),
            ["AA:BB:CC:DD:EE:FF"],
        )


class TestIsAirpods(unittest.TestCase):
    def test_true(self):
        self.assertTrue(bluez.is_airpods(INFO_YES))

    def test_false_connected_no(self):
        self.assertFalse(bluez.is_airpods(INFO_NO))

    def test_false_no_uuid(self):
        text = INFO_YES.replace("74ec2172-0bad-4d01-8f77-997b2be0722a", "00000000-0000-0000-0000-000000000000")
        self.assertFalse(bluez.is_airpods(text))

    def test_false_uuid_only_in_name(self):
        text = INFO_YES.replace(
            "\tUUID: Vendor specific           (74ec2172-0bad-4d01-8f77-997b2be0722a)\n",
            "",
        ).replace("Name: AirPodsD. Pro", "Name: 74ec2172-0bad-4d01-8f77-997b2be0722a")
        self.assertFalse(bluez.is_airpods(text))


class TestFind(unittest.TestCase):
    def _fake_run(self, devices, infos):
        def _run(args):
            if args[:2] == ["devices", "Connected"]:
                return devices
            addr = args[1]
            return infos.get(addr, "")
        return _run

    def test_zero(self):
        run = self._fake_run(DEVICES, {})
        self.assertIsNone(bluez.find_airpods(run=run))

    def test_one(self):
        run = self._fake_run(DEVICES, {"AA:BB:CC:DD:EE:FF": INFO_YES})
        self.assertEqual(bluez.find_airpods(run=run), "AA:BB:CC:DD:EE:FF")

    def test_two(self):
        run = self._fake_run(DEVICES, {"AA:BB:CC:DD:EE:FF": INFO_YES, "11:22:33:44:55:66": INFO_YES})
        self.assertIsNone(bluez.find_airpods(run=run))

    def test_run_empty(self):
        run = self._fake_run("", {})
        self.assertIsNone(bluez.find_airpods(run=run))


class TestRun(unittest.TestCase):
    def test_missing_bluetoothctl(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(bluez.run(["--non-esiste"]), "")


if __name__ == "__main__":
    unittest.main()
