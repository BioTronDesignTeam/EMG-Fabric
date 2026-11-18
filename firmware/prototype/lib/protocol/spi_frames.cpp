#include "spi_frames.h"

#include "crc16.h"
#include "emg_bytes.h"

namespace emg {

namespace {
constexpr size_t kOffFirstFrame = 4;
constexpr size_t kOffSamples = 8;
constexpr size_t kOffCrc = 30;
}  // namespace

// Fields are written byte by byte (see emg_bytes.h), so the result is the same on any mcu, whatever its byte order or alignment rules.
void encode_slave_frame(uint8_t flags, uint32_t first_frame, const int16_t* samples, uint8_t out[kSpiFrameSize]) {
    out[0] = kSlaveMagic;
    out[1] = kProtocolVersion;
    out[2] = flags;
    out[3] = 0;
    put_u32(out + kOffFirstFrame, first_frame);
    for (size_t i = 0; i < kSamplesPerFrame; ++i) put_i16(out + kOffSamples + 2 * i, samples[i]);
    out[28] = 0;
    out[29] = 0;
    put_u16(out + kOffCrc, crc16_ccitt(out, kOffCrc));
}

bool decode_slave_frame(const uint8_t in[kSpiFrameSize], SlaveFrame* out) {
    if (in[0] != kSlaveMagic || in[1] != kProtocolVersion) return false;
    if (crc16_ccitt(in, kOffCrc) != get_u16(in + kOffCrc)) return false;
    out->magic = in[0];
    out->version = in[1];
    out->flags = in[2];
    out->reserved0 = in[3];
    out->first_frame = get_u32(in + kOffFirstFrame);
    for (size_t i = 0; i < kSamplesPerFrame; ++i) out->samples[i] = get_i16(in + kOffSamples + 2 * i);
    out->reserved1 = get_u16(in + 28);
    out->crc = get_u16(in + kOffCrc);
    return true;
}

uint8_t mode_flags(uint8_t mode) {
    // mode --> flag bits
    return mode == kModeSynthetic ? kFlagSynthetic : kFlagCounter;
}

}  // namespace emg
