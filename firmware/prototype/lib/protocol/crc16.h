// crc16.h
// interface for the crc16 checksum for our data packets.
// CRC can be thought of as obtaining the remainder from doing long division
// on the data bits.

// We use 'divisor': 0x1021, no bit reflection and no final xor.
// Check value: crc16_ccitt("123456789") == 0x29B1.


// Used by both the SPI frames and the host packets. The Python receiver has
// an identical implementation (Software/prototype/emg_protocol.py).
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace emg {

constexpr uint16_t kCrcInit = 0xFFFF; // all 1s as init value

// Continues the 'division' process on an existing CRC.
// This is used when our data bits are not contiguous in memory.
uint16_t crc16_ccitt_update(uint16_t crc, const uint8_t* data, size_t len);

// Calculate CRC given the full data.
inline uint16_t crc16_ccitt(const uint8_t* data, size_t len) {
    return crc16_ccitt_update(kCrcInit, data, len);
}

}
