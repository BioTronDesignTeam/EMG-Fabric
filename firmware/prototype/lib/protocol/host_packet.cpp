#include "host_packet.h"

#include <string.h>

#include "crc16.h"
#include "emg_bytes.h"

namespace emg {

size_t encode_host_packet(uint8_t type, uint16_t seq, const uint8_t* payload, uint16_t len, uint8_t* out, size_t out_cap) {
    const size_t total = kHostHeaderSize + len + kHostCrcSize;
    if (len > kHostMaxPayload || total > out_cap) return 0;
    out[0] = kHostSync0;
    out[1] = kHostSync1;
    out[2] = kHostVersion;
    out[3] = type;
    put_u16(out + 4, seq);
    put_u16(out + 6, len);
    if (len > 0) memcpy(out + kHostHeaderSize, payload, len);
    // The CRC covers version..payload: everything except the two sync bytes.
    put_u16(out + kHostHeaderSize + len, crc16_ccitt(out + 2, kHostHeaderSize - 2 + len));
    return total;
}

// Streaming parser =====================================================================

void HostPacketParser::drop(size_t count) {
    if (count >= n_) {
        n_ = 0;
        return;
    }
    memmove(buf_, buf_ + count, n_ - count); // shift contents in array "forward" by |count|
    n_ -= count;
}

void HostPacketParser::feed(uint8_t b) {
    if (n_ == sizeof(buf_)) drop(1);  // caller forgot next(), lose the oldest byte
    buf_[n_++] = b;
}

bool HostPacketParser::next(HostPacket* out) {
    // buf_ always starts at a possible packet start. Each failed check drops
    // exactly one byte and tries again, so a real packet right after garbage
    // or a corrupted packet is still found.
    for (;;) {
        size_t skip = 0;
        // skip until we reach first sync byte
        while (skip < n_ && buf_[skip] != kHostSync0) ++skip;
        drop(skip);
        if (n_ < 2) return false;
        if (buf_[1] != kHostSync1) {
            drop(1);
            continue;
        }
        if (n_ < 3) return false;
        if (buf_[2] != kHostVersion) {
            drop(1);
            continue;
        }
        if (n_ < kHostHeaderSize) return false;
        const uint16_t len = get_u16(buf_ + 6);
        if (len > kHostMaxPayload) {
            drop(1);
            continue;
        }
        const size_t total = kHostHeaderSize + len + kHostCrcSize;
        if (n_ < total) return false;  // wait for the rest
        if (crc16_ccitt(buf_ + 2, kHostHeaderSize - 2 + len) != get_u16(buf_ + kHostHeaderSize + len)) {
            ++crc_errors_;
            drop(1);
            continue;
        }
        out->type = buf_[3];
        out->seq = get_u16(buf_ + 4);
        out->len = len;
        if (len > 0) memcpy(out->payload, buf_ + kHostHeaderSize, len);
        drop(total);
        return true;
    }
}

// ---- Payloads ---------------------------------------------------------------
const size_t kSlotDataSize = 1 + 4 + 2 * kSamplesPerFrame;  // 25
const size_t kSlotStatusSize = 13;

size_t build_data_payload(const DataPayload& d, uint8_t* out, size_t cap) {
    size_t n = 5;
    if (cap < n) return 0;
    put_u32(out, d.tick);
    out[4] = d.slot_mask;
    for (size_t s = 0; s < kMaxSlots; ++s) {
        if (!(d.slot_mask & (1u << s))) continue;
        if (n + kSlotDataSize > cap) return 0;
        const SlotSamples& slot = d.slots[s];
        out[n] = slot.flags;
        put_u32(out + n + 1, slot.first_frame);
        for (size_t i = 0; i < kSamplesPerFrame; ++i) put_i16(out + n + 5 + 2 * i, slot.samples[i]);
        n += kSlotDataSize;
    }
    return n;
}

bool parse_data_payload(const uint8_t* p, size_t len, DataPayload* out) {
    if (len < 5) return false;
    const uint8_t mask = p[4];
    if (mask >> kMaxSlots) return false;  // bits above slot 3 are invalid
    size_t count = 0;
    for (size_t s = 0; s < kMaxSlots; ++s) count += (mask >> s) & 1u;
    if (len != 5 + count * kSlotDataSize) return false;

    memset(out, 0, sizeof(*out));
    out->tick = get_u32(p);
    out->slot_mask = mask;
    size_t n = 5;
    for (size_t s = 0; s < kMaxSlots; ++s) {
        if (!(mask & (1u << s))) continue;
        SlotSamples& slot = out->slots[s];
        slot.flags = p[n];
        slot.first_frame = get_u32(p + n + 1);
        for (size_t i = 0; i < kSamplesPerFrame; ++i) slot.samples[i] = get_i16(p + n + 5 + 2 * i);
        n += kSlotDataSize;
    }
    return true;
}

size_t build_status_payload(const StatusPayload& s, uint8_t* out, size_t cap) {
    const size_t len = 5 + kMaxSlots * kSlotStatusSize;  // 57
    if (cap < len) return 0;
    put_u32(out, s.uptime_ms);
    out[4] = s.present_mask;
    for (size_t i = 0; i < kMaxSlots; ++i) {
        uint8_t* q = out + 5 + i * kSlotStatusSize;
        put_u32(q, s.slots[i].crc_errors);
        put_u32(q + 4, s.slots[i].gaps);
        put_u32(q + 8, s.slots[i].overruns);
        q[12] = s.slots[i].last_flags;
    }
    return len;
}

bool parse_status_payload(const uint8_t* p, size_t len, StatusPayload* out) {
    if (len != 5 + kMaxSlots * kSlotStatusSize) return false;
    out->uptime_ms = get_u32(p);
    out->present_mask = p[4];
    for (size_t i = 0; i < kMaxSlots; ++i) {
        const uint8_t* q = p + 5 + i * kSlotStatusSize;
        out->slots[i].crc_errors = get_u32(q);
        out->slots[i].gaps = get_u32(q + 4);
        out->slots[i].overruns = get_u32(q + 8);
        out->slots[i].last_flags = q[12];
    }
    return true;
}

}  // namespace emg
