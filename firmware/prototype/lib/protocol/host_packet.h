// host_packet.h - framed binary packets between the master and the laptop.
//
// Packet layout (little-endian):
//   u8 0xAA, 
//   u8 0x55,           sync bytes: indicating start of packet
//   u8 version (=2),   
//   u8 type,           data, log, cmd, status.
//   u16 seq,           +1 per packet sent, so the laptop can spot lost packets
//   u16 len, payload[len],
//   u16 crc             CRC-16 over version..payload
//
// A serial port is just a byte stream. Bytes can get lost or corrupted, and
// the ESP32 prints boot text when it resets. So the parser looks for 0xAA 0x55,
// checks the header, waits for `len` bytes and accepts the packet only if the
// CRC matches. On any failure it skips ONE byte and searches again, which
// re-locks onto the next real packet.
//
// The Python receiver mirrors this (Software/prototype/emg_protocol.py). Both
// are tested against test/golden/host_packets_v2.txt.
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "spi_frames.h"  // kSamplesPerFrame

namespace emg {

constexpr uint8_t kHostSync0 = 0xAA;
constexpr uint8_t kHostSync1 = 0x55;
constexpr uint8_t kHostVersion = 2;
constexpr size_t kHostHeaderSize = 8;  // sync(2) + version + type + seq(2) + len(2)
constexpr size_t kHostCrcSize = 2;
constexpr size_t kHostMaxPayload = 256; // in bytes
constexpr size_t kHostMaxPacket = kHostHeaderSize + kHostMaxPayload + kHostCrcSize;

// Packet types.
constexpr uint8_t kPktData = 0x01;    // master -> laptop, every 10 ms: samples from all slaves
constexpr uint8_t kPktStatus = 0x02;  // master -> laptop, every 1 s: per-slave counters
constexpr uint8_t kPktLog = 0x04;     // master -> laptop: UTF-8 text (the master never prints raw text)
constexpr uint8_t kPktCmd = 0x10;     // laptop -> master: u8 command (for future expansion as well)

// Commands (CMD payload byte 0).
constexpr uint8_t kCmdResetStats = 1;

constexpr size_t kMaxSlots = 4;  // slave slots on the master (one CS pin each)

// Build a complete packet into `out`. Returns its size, or 0 if it doesn't fit.
size_t encode_host_packet(uint8_t type, uint16_t seq, const uint8_t* payload, uint16_t len, uint8_t* out, size_t out_cap);

struct HostPacket {
    uint8_t type;
    uint16_t seq;
    uint16_t len;
    uint8_t payload[kHostMaxPayload];
};

// Streaming parser:   parser.feed(byte);  while (parser.next(&pkt)) handle(pkt);
// this basically keeps a buffer of bytes, it checks whether what it has in that buffer is a valid packet.
// it does this by checking for sync bytes, if not found, it discards
class HostPacketParser {
public:
    HostPacketParser() : n_(0), crc_errors_(0) {}
    void feed(uint8_t b); // feeds into buffer
    bool next(HostPacket* out); // checks and extracts packet from buffer if it exists + is valid
    uint32_t crc_errors() const { return crc_errors_; }

private:
    uint8_t buf_[kHostMaxPacket]; // basically a flat array
    size_t n_; // size of content in buffer.
    uint32_t crc_errors_;
    
    void drop(size_t count);
};

// ===========================================================================================
// ===========================================================================================
// Payload types =============================================================================

// DATA 
struct SlotSamples {
    uint8_t flags; // flags for slave data
    uint32_t first_frame;  // the slave's own counter (used to check whether slave is in sync)
    int16_t samples[kSamplesPerFrame];
};
struct DataPayload {
    uint32_t tick; // ms since master started
    uint8_t slot_mask; // bit i set = slots[i] is valid
    SlotSamples slots[kMaxSlots];
};

// STATUS
struct SlotStatus {
    // all counters:
    uint32_t crc_errors; // corrupted frames from a connected slave
    uint32_t gaps; // 10-sample batches not delivered while connected
    uint32_t overruns; // frames where the slave reported a dropped batch

    // copy of flags from most recent valid frame, used to show what each slave is supposed to be doing
    // even when no data is getting through.
    uint8_t last_flags;
};
struct StatusPayload {
    uint32_t uptime_ms;
    uint8_t present_mask;  // bit i set = a slave is connected in slot i
    SlotStatus slots[kMaxSlots];
};

// build_*: write the payload into `out`; return its length (0 if it doesn't fit).
// parse_*: return false if `len` is wrong.
size_t build_data_payload(const DataPayload& d, uint8_t* out, size_t cap);
bool parse_data_payload(const uint8_t* p, size_t len, DataPayload* out);
size_t build_status_payload(const StatusPayload& s, uint8_t* out, size_t cap);
bool parse_status_payload(const uint8_t* p, size_t len, StatusPayload* out);

}  // namespace emg
