// CRC-16/CCITT-FALSE tests.
#include <string.h>
#include <unity.h>

#include "crc16.h"

using namespace emg;

void setUp() {}
void tearDown() {}

// The standard "check" value for CRC-16/CCITT-FALSE.
static void test_check_value() {
    const char* s = "123456789";
    TEST_ASSERT_EQUAL_HEX16(0x29B1, crc16_ccitt(reinterpret_cast<const uint8_t*>(s), strlen(s)));
}

static void test_empty_is_init() {
    TEST_ASSERT_EQUAL_HEX16(0xFFFF, crc16_ccitt(nullptr, 0));
}

static void test_incremental_equals_one_shot() {
    const uint8_t data[] = {0xA5, 0x01, 0x02, 0x03, 0x10, 0x20, 0x30, 0x40, 0xFF};
    uint16_t crc = crc16_ccitt_update(kCrcInit, data, 4);
    crc = crc16_ccitt_update(crc, data + 4, sizeof(data) - 4);
    TEST_ASSERT_EQUAL_HEX16(crc16_ccitt(data, sizeof(data)), crc);
}

static void test_single_bit_flip_detected() {
    uint8_t data[36];
    for (int i = 0; i < 36; ++i) data[i] = static_cast<uint8_t>(i * 7);
    const uint16_t good = crc16_ccitt(data, sizeof(data));
    for (int byte = 0; byte < 36; ++byte) {
        for (int bit = 0; bit < 8; ++bit) {
            data[byte] ^= static_cast<uint8_t>(1u << bit);
            TEST_ASSERT_NOT_EQUAL(good, crc16_ccitt(data, sizeof(data)));
            data[byte] ^= static_cast<uint8_t>(1u << bit);
        }
    }
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_check_value);
    RUN_TEST(test_empty_is_init);
    RUN_TEST(test_incremental_equals_one_shot);
    RUN_TEST(test_single_bit_flip_detected);
    return UNITY_END();
}
