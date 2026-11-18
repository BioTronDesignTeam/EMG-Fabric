"""Tests for emg_protocol.py.  Run:  python -m unittest -v test_protocol

Uses the same golden file as the C tests (firmware/prototype/test/test_host_packet),
so passing both means the firmware and the laptop agree byte for byte.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import emg_protocol as p

GOLDEN = Path(__file__).resolve().parents[2] / "firmware" / "prototype" / "test" / "golden" / "host_packets_v2.txt"


def ints(s: str) -> list[int]:
    return [int(x) for x in s.split(",")] if s else []


class TestGolden(unittest.TestCase):
    def test_golden_cases(self) -> None:
        cases = [
            dict(tok.split("=", 1) for tok in line.split() if "=" in tok)
            for line in GOLDEN.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        self.assertGreaterEqual(len(cases), 8)
        for c in cases:
            with self.subTest(case=c["case"]):
                raw = bytes.fromhex(c["hex"])
                parser = p.PacketParser()
                pkts = parser.feed(raw)
                if c.get("stream") == "1":
                    self.assertEqual([k.seq for k in pkts], ints(c["expect_seqs"]))
                    self.assertEqual(parser.crc_errors, int(c["expect_crc_errors"]))
                elif c["valid"] == "0":
                    self.assertEqual(pkts, [])
                else:
                    self.assertEqual(len(pkts), 1)
                    k = pkts[0]
                    self.assertEqual((k.type, k.seq), (int(c["type"]), int(c["seq"])))
                    self.assertEqual(k.payload, bytes.fromhex(c["payload"]))
                    self.assertEqual(p.encode_packet(k.type, k.seq, k.payload), raw)
                    self.check_fields(c, k)

    def check_fields(self, c: dict[str, str], k: p.Packet) -> None:
        if k.type == p.PKT_DATA:
            d = p.decode_data(k.payload)
            self.assertEqual(d.tick, int(c["tick"]))
            self.assertEqual(sum(1 << s for s in d.slots), int(c["mask"]))
            for s, e in d.slots.items():
                self.assertEqual(e.flags, int(c[f"s{s}_flags"]))
                self.assertEqual(e.first_frame, int(c[f"s{s}_first"]))
                self.assertEqual(e.samples, ints(c[f"s{s}_samples"]))
            self.assertEqual(p.encode_data(d), k.payload)
        elif k.type == p.PKT_STATUS:
            s = p.decode_status(k.payload)
            self.assertEqual((s.uptime_ms, s.present_mask), (int(c["uptime"]), int(c["present"])))
            self.assertEqual([e.crc_errors for e in s.slots], ints(c["crc_errors"]))
            self.assertEqual([e.gaps for e in s.slots], ints(c["gaps"]))
            self.assertEqual([e.overruns for e in s.slots], ints(c["overruns"]))
            self.assertEqual([e.last_flags for e in s.slots], ints(c["last_flags"]))
            self.assertEqual(p.encode_status(s), k.payload)


class TestParser(unittest.TestCase):
    def test_crc_check_value(self) -> None:
        self.assertEqual(p.crc16_ccitt(b"123456789"), 0x29B1)

    def test_byte_by_byte(self) -> None:
        stream = b"".join(p.encode_packet(p.PKT_LOG, i, bytes([i])) for i in range(20))
        parser = p.PacketParser()
        got = [k for b in stream for k in parser.feed(bytes([b]))]
        self.assertEqual([k.seq for k in got], list(range(20)))

    def test_resync_after_garbage_and_corruption(self) -> None:
        good = [p.encode_packet(p.PKT_LOG, i, b"x" * i) for i in range(5)]
        bad = bytearray(good[2])
        bad[10] ^= 0x40
        stream = b"\xAA\xAA\x55\x00junk" + good[0] + good[1] + bytes(bad) + good[3] + b"\xAA" + good[4]
        parser = p.PacketParser()
        self.assertEqual([k.seq for k in parser.feed(stream)], [0, 1, 3, 4])
        self.assertEqual(parser.crc_errors, 1)


class TestCounterCheck(unittest.TestCase):
    def test_counter_pattern(self) -> None:
        e = p.SlotSamples(p.FLAG_COUNTER, 4093, [(4093 + i) & 0xFFF for i in range(10)])
        self.assertEqual(p.counter_errors(e), 0)
        e.samples[4] += 1
        self.assertEqual(p.counter_errors(e), 1)


if __name__ == "__main__":
    unittest.main()
