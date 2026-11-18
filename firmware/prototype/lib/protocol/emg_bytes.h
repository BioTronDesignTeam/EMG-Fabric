// emg_bytes.h - write numbers into byte arrays and read them back.
//
// Always little-endian (lowest byte first), byte by byte, so the result is
// the same on every chip regardless of its own byte order or alignment rules.
//   put_u32(p, 0x12345678)   ->   p = 78 56 34 12

#pragma once

#include <stdint.h>

namespace emg {

inline void put_u16(uint8_t* p, uint16_t v) {
    p[0] = static_cast<uint8_t>(v);
    p[1] = static_cast<uint8_t>(v >> 8);
}

inline void put_u32(uint8_t* p, uint32_t v) {
    p[0] = static_cast<uint8_t>(v);
    p[1] = static_cast<uint8_t>(v >> 8);
    p[2] = static_cast<uint8_t>(v >> 16);
    p[3] = static_cast<uint8_t>(v >> 24);
}

inline void put_i16(uint8_t* p, int16_t v) { put_u16(p, static_cast<uint16_t>(v)); }

inline uint16_t get_u16(const uint8_t* p) {
    return static_cast<uint16_t>(p[0] | (p[1] << 8));
}

inline uint32_t get_u32(const uint8_t* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
           (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

inline int16_t get_i16(const uint8_t* p) { return static_cast<int16_t>(get_u16(p)); }

}
