"""Test per protocol.py."""

import random
import unittest

import protocol


class TestParseBattery(unittest.TestCase):
    def test_example(self):
        data = bytes.fromhex("04000400040003020164020104016301010801110201")
        self.assertEqual(protocol.parse(data), {
            "battery": {
                "right": {"level": 100, "charging": False},
                "left": {"level": 99, "charging": True},
                "case": {"level": 17, "charging": False},
            }
        })

    def test_case_only(self):
        # HEADER + 04 00 + 01 + block [08 01 50 01 01] (case, 80, in carica)
        data = bytes.fromhex("040004000400010801500101")
        self.assertEqual(protocol.parse(data), {
            "battery": {"case": {"level": 80, "charging": True}}
        })

    def test_disconnected_state(self):
        # HEADER + 04 00 + 01 + [04 01 50 04 01] (left, scollegato)
        data = bytes.fromhex("040004000400010401500401")
        self.assertEqual(protocol.parse(data), {
            "battery": {"left": {"level": None, "charging": None}}
        })

    def test_repeated_component_returns_none(self):
        # due blocchi left -> None
        data = bytes.fromhex("04000400040002" + "040163010101" * 2)
        self.assertIsNone(protocol.parse(data))

    def test_n_zero_and_four(self):
        self.assertIsNone(protocol.parse(bytes.fromhex("04000400040000")))
        data = bytes.fromhex("04000400040004" + "040163010101" * 4)
        self.assertIsNone(protocol.parse(data))

    def test_wrong_length(self):
        data = bytes.fromhex("040004000400010801500101")[:-1]
        self.assertIsNone(protocol.parse(data))

    def test_level_over_100(self):
        # level 0x65 = 101, stato non 0x04 -> None
        data = bytes.fromhex("040004000400010801650101")
        self.assertIsNone(protocol.parse(data))


class TestParseMode(unittest.TestCase):
    def test_roundtrip_all_modes(self):
        for name in protocol.MODES:
            self.assertEqual(protocol.parse(protocol.mode_packet(name)), {"mode": name})

    def test_mode_packet_bad_name_raises(self):
        with self.assertRaises(ValueError):
            protocol.mode_packet("xyz")

    def test_unknown_opcode_returns_none(self):
        data = protocol.HEADER + b"\x06\x00\x01\x02"
        self.assertIsNone(protocol.parse(data))

    def test_handshake_returns_none(self):
        self.assertIsNone(protocol.parse(protocol.HANDSHAKE))


class TestRandomRobustness(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(protocol.parse(b""))

    def test_random_sequences_never_raise(self):
        rng = random.Random(1)
        for _ in range(2000):
            length = rng.randint(0, 40)
            data = bytes(rng.randint(0, 255) for _ in range(length))
            if rng.random() < 0.5:
                data = protocol.HEADER + data
            protocol.parse(data)  # non deve sollevare


if __name__ == "__main__":
    unittest.main()
