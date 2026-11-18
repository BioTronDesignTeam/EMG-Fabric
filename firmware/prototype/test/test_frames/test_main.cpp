// SPI frame size, layout and encode/decode.
#include <stddef.h>
#include <string.h>
#include <unity.h>

#include "crc16.h"
#include "spi_frames.h"

using namespace emg;

void setUp() {}
void tearDown() {}

static const int16_t kSamples[10] = {-4000, -3000, -2000, -1000, 0, 1000, 2000, 3000, 4095, -32768};

static void test_size_and_offsets() {
    TEST_ASSERT_EQUAL(32, sizeof(SlaveFrame));
    TEST_ASSERT_EQUAL(0, kSpiFrameSize % 4);  // ESP32 SPI slave DMA needs a multiple of 4
    TEST_ASSERT_EQUAL(4, offsetof(SlaveFrame, first_frame));
    TEST_ASSERT_EQUAL(8, offsetof(SlaveFrame, samples));
    TEST_ASSERT_EQUAL(30, offsetof(SlaveFrame, crc));
}

static void test_wire_layout_is_little_endian() {
    uint8_t buf[32];
    encode_slave_frame(kFlagCounter, 0xDEADBEEF, kSamples, buf);
    TEST_ASSERT_EQUAL_HEX8(0xA5, buf[0]);
    TEST_ASSERT_EQUAL_HEX8(2, buf[1]);
    TEST_ASSERT_EQUAL_HEX8(kFlagCounter, buf[2]);
    TEST_ASSERT_EQUAL_HEX8(0xEF, buf[4]);  // least significant byte first
    TEST_ASSERT_EQUAL_HEX8(0xDE, buf[7]);
    TEST_ASSERT_EQUAL_HEX8(0x60, buf[8]);  // -4000 = 0xF060
    TEST_ASSERT_EQUAL_HEX8(0xF0, buf[9]);
    const uint16_t crc = crc16_ccitt(buf, 30);
    TEST_ASSERT_EQUAL_HEX8(crc & 0xFF, buf[30]);
    TEST_ASSERT_EQUAL_HEX8(crc >> 8, buf[31]);
}

static void test_round_trip() {
    uint8_t buf[32];
    encode_slave_frame(kFlagSynthetic | kFlagOverrun, 123456, kSamples, buf);
    SlaveFrame f;
    TEST_ASSERT_TRUE(decode_slave_frame(buf, &f));
    TEST_ASSERT_EQUAL(kFlagSynthetic | kFlagOverrun, f.flags);
    TEST_ASSERT_EQUAL_UINT32(123456, f.first_frame);
    for (int i = 0; i < 10; ++i) TEST_ASSERT_EQUAL_INT16(kSamples[i], f.samples[i]);
}

static void test_rejects_bad_frames() {
    uint8_t buf[32];
    SlaveFrame f;
    encode_slave_frame(kFlagCounter, 1, kSamples, buf);
    buf[12] ^= 0x01;  // one flipped bit
    TEST_ASSERT_FALSE(decode_slave_frame(buf, &f));
    buf[12] ^= 0x01;
    buf[1] = 1;  // old protocol version
    TEST_ASSERT_FALSE(decode_slave_frame(buf, &f));
    memset(buf, 0xFF, sizeof(buf));  // nothing connected
    TEST_ASSERT_FALSE(decode_slave_frame(buf, &f));
    memset(buf, 0x00, sizeof(buf));
    TEST_ASSERT_FALSE(decode_slave_frame(buf, &f));
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_size_and_offsets);
    RUN_TEST(test_wire_layout_is_little_endian);
    RUN_TEST(test_round_trip);
    RUN_TEST(test_rejects_bad_frames);
    return UNITY_END();
}
