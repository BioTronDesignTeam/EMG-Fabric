"""Laptop side of the master <-> laptop protocol (v2). Mirrors
firmware/prototype/lib/protocol/host_packet.cpp; both are tested against
firmware/prototype/test/golden/host_packets_v2.txt.

Packet: AA 55 | version(1) type(1) seq(u16) len(u16) | payload[len] | crc(u16)
Little-endian; CRC-16/CCITT-FALSE over version..payload.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

VERSION = 2
HEADER_SIZE = 8
CRC_SIZE = 2
MAX_PAYLOAD = 256
MAX_SLOTS = 4
SAMPLES_PER_FRAME = 10

PKT_DATA = 0x01
PKT_STATUS = 0x02
PKT_LOG = 0x04
PKT_CMD = 0x10

CMD_RESET_STATS = 1

FLAG_OVERRUN = 1 << 0
FLAG_COUNTER = 1 << 1
FLAG_SYNTHETIC = 1 << 2


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    """CRC-16/CCITT-FALSE: poly 0x1021, init 0xFFFF. crc16_ccitt(b"123456789") == 0x29B1."""
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def flags_str(flags: int) -> str:
    names = ["synthetic" if flags & FLAG_SYNTHETIC else "counter"]
    if flags & FLAG_OVERRUN:
        names.append("overrun")
    return "|".join(names)


# --------------------------------------------------------------------------- packets

@dataclass
class Packet:
    type: int
    seq: int
    payload: bytes


def encode_packet(ptype: int, seq: int, payload: bytes) -> bytes:
    body = struct.pack("<BBHH", VERSION, ptype, seq & 0xFFFF, len(payload)) + payload
    return b"\xAA\x55" + body + struct.pack("<H", crc16_ccitt(body))


class PacketParser:
    """Streaming parser. Same rule as the C parser: any failed check drops
    ONE byte and searches again, so it re-locks onto the next real packet."""

    def __init__(self) -> None:
        self.buf = bytearray()
        self.crc_errors = 0

    def feed(self, data: bytes) -> list[Packet]:
        buf = self.buf
        buf += data
        out: list[Packet] = []
        while True:
            i = buf.find(0xAA)
            if i < 0:
                buf.clear()
                break
            del buf[:i]
            if len(buf) < 3:
                break
            if buf[1] != 0x55 or buf[2] != VERSION:
                del buf[:1]
                continue
            if len(buf) < HEADER_SIZE:
                break
            (length,) = struct.unpack_from("<H", buf, 6)
            if length > MAX_PAYLOAD:
                del buf[:1]
                continue
            total = HEADER_SIZE + length + CRC_SIZE
            if len(buf) < total:
                break
            (want,) = struct.unpack_from("<H", buf, HEADER_SIZE + length)
            if crc16_ccitt(bytes(buf[2:HEADER_SIZE + length])) != want:
                self.crc_errors += 1
                del buf[:1]
                continue
            _, ptype, seq = struct.unpack_from("<BBH", buf, 2)
            out.append(Packet(ptype, seq, bytes(buf[HEADER_SIZE:HEADER_SIZE + length])))
            del buf[:total]
        return out


# --------------------------------------------------------------------------- payloads

_SLOT = struct.Struct(f"<BI{SAMPLES_PER_FRAME}h")  # flags, first_frame, samples: 25 bytes
_SLOT_STATUS = struct.Struct("<IIIB")              # crc_errors, gaps, overruns, last_flags: 13 bytes


@dataclass
class SlotSamples:
    flags: int
    first_frame: int  # the slave's own sample counter
    samples: list[int]


@dataclass
class Data:
    tick: int                                                     # master SYNC pulse number of samples[0]
    slots: dict[int, SlotSamples] = field(default_factory=dict)   # slot index 0..3 -> samples


@dataclass
class SlotStatus:
    crc_errors: int
    gaps: int
    overruns: int
    last_flags: int


@dataclass
class Status:
    uptime_ms: int
    present_mask: int
    slots: list[SlotStatus]


def encode_data(d: Data) -> bytes:
    mask = sum(1 << s for s in d.slots)
    out = struct.pack("<IB", d.tick, mask)
    for s in sorted(d.slots):
        e = d.slots[s]
        out += _SLOT.pack(e.flags, e.first_frame, *e.samples)
    return out


def decode_data(p: bytes) -> Data:
    if len(p) < 5:
        raise ValueError("DATA too short")
    tick, mask = struct.unpack_from("<IB", p, 0)
    slots = [s for s in range(MAX_SLOTS) if mask & (1 << s)]
    if mask >> MAX_SLOTS or len(p) != 5 + len(slots) * _SLOT.size:
        raise ValueError("DATA length mismatch")
    d = Data(tick)
    for k, s in enumerate(slots):
        flags, first, *samples = _SLOT.unpack_from(p, 5 + k * _SLOT.size)
        d.slots[s] = SlotSamples(flags, first, samples)
    return d


def encode_status(s: Status) -> bytes:
    out = struct.pack("<IB", s.uptime_ms, s.present_mask)
    for e in s.slots:
        out += _SLOT_STATUS.pack(e.crc_errors, e.gaps, e.overruns, e.last_flags)
    return out


def decode_status(p: bytes) -> Status:
    if len(p) != 5 + MAX_SLOTS * _SLOT_STATUS.size:
        raise ValueError("STATUS length mismatch")
    uptime, mask = struct.unpack_from("<IB", p, 0)
    slots = [SlotStatus(*_SLOT_STATUS.unpack_from(p, 5 + i * _SLOT_STATUS.size)) for i in range(MAX_SLOTS)]
    return Status(uptime, mask, slots)


def encode_cmd(cmd: int) -> bytes:
    return bytes([cmd])


def counter_errors(e: SlotSamples) -> int:
    """Samples that differ from the counter test pattern (first_frame + i) & 0x0FFF."""
    return sum(1 for i, s in enumerate(e.samples) if s != ((e.first_frame + i) & 0x0FFF))
