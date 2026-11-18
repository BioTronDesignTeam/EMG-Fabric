// spi_frames.h
// the SPI frame each slave sends to the master
//
// Every 10 ms the master reads 32 bytes from each slave. The data only goes
// one way: the master sends nothing useful back, so there is no MasterFrame.
//
// Layout, 32 bytes:
//   0      magic = 0xA5
//   1      version = 2
//   2      flags
//   3      reserved, 0       padding for future expansion
//   4..7   u32 first_frame   the slave's own count of SYNC pulses at samples[0]
//   8..27  i16 samples[10]   one sample per SYNC pulse (1 kHz)
//   28..29 reserved, 0       padding
//   30..31 u16 crc           CRC16 over bytes 0..29

#pragma once

#include <stddef.h>
#include <stdint.h>

namespace emg {

constexpr uint8_t kSlaveMagic = 0xA5; // can be anything technically, identifier for our emg frames, 
                                      // if in future we send different data via spi frames we would use a different magic for that one.
constexpr uint8_t kProtocolVersion = 2;
constexpr size_t kSamplesPerFrame = 10;  // 10 samples at 1 kHz = one read every 10 ms
constexpr size_t kSpiFrameSize = 32;

// flags bits
// total 8 bits can be used for flags, this uses 3: 
constexpr uint8_t kFlagOverrun = 1u << 0;    // (1) the slave dropped a batch: the master didn't read in time
constexpr uint8_t kFlagCounter = 1u << 1;    // (2) samples are the counter test pattern
constexpr uint8_t kFlagSynthetic = 1u << 2;  // (4) samples are synthetic EMG

// What the slave samples (chosen at build time with -DSLAVE_MODE=...)
constexpr uint8_t kModeCounter = 1;    // sample = sample number & 0x0FFF: any loss is detectable
constexpr uint8_t kModeSynthetic = 2;  // EMG-like noise bursts, for plots

struct SlaveFrame {
    uint8_t magic;
    uint8_t version;
    uint8_t flags;
    uint8_t reserved0;
    uint32_t first_frame;
    int16_t samples[kSamplesPerFrame];
    uint16_t reserved1;
    uint16_t crc;
};
// Documents the layout only: encoding is done byte by byte (see emg_bytes.h).
static_assert(sizeof(SlaveFrame) == kSpiFrameSize, "SlaveFrame size does not match kSpiFrameSize requirement.");

// Write the 32 wire bytes (magic, version and CRC are filled in here).
void encode_slave_frame(uint8_t flags, uint32_t first_frame, const int16_t* samples, uint8_t out[kSpiFrameSize]);

// Parse 32 wire bytes. Returns false (and leaves *out alone) if errors are detected.
bool decode_slave_frame(const uint8_t in[kSpiFrameSize], SlaveFrame* out);

// Sample mode --> flag bits
uint8_t mode_flags(uint8_t mode);

}  // namespace emg
