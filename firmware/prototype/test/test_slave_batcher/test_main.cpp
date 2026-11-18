// Slave side: sample sources and the batcher.
#include <unity.h>

#include "sample_source.h"
#include "slave_batcher.h"

using namespace emg;

void setUp() {}
void tearDown() {}

static void test_counter_pattern_is_12_bit_sample_number() {
    SampleSource src(kModeCounter);
    const uint32_t ns[] = {0, 1, 4095, 4096, 4097, 123456789};
    for (size_t i = 0; i < sizeof(ns) / sizeof(ns[0]); ++i) {
        TEST_ASSERT_EQUAL_INT16(static_cast<int16_t>(ns[i] & 0x0FFF), src.read_sample(ns[i]));
    }
}

static void test_synthetic_in_range_and_bursts() {
    SampleSource src(kModeSynthetic);
    int32_t rest = 0, peak = 0;
    for (uint32_t n = 0; n < 4000; ++n) {
        const int16_t s = src.read_sample(n);
        TEST_ASSERT_TRUE(s >= 0 && s <= 4095);
        const int32_t dev = s > 2048 ? s - 2048 : 2048 - s;
        const uint32_t t = n % 2000;
        if (t < 800 && dev > rest) rest = dev;
        if (t >= 1000 && t < 1600 && dev > peak) peak = dev;
    }
    TEST_ASSERT_TRUE(rest <= 40);  // quiet at rest
    TEST_ASSERT_TRUE(peak > 600);  // loud during a "contraction"
}

static int16_t add(SlaveBatcher& b, uint8_t* buf) {
    return b.add_sample(static_cast<int16_t>(b.next_sample_number()), buf) ? 1 : 0;
}

static void test_frame_every_10_samples_when_read() {
    SlaveBatcher b(kFlagCounter);
    uint8_t buf[32];
    SlaveFrame f;
    for (int batch = 0; batch < 5; ++batch) {
        for (int i = 0; i < 9; ++i) TEST_ASSERT_EQUAL(0, add(b, buf));
        TEST_ASSERT_EQUAL(1, add(b, buf));
        TEST_ASSERT_TRUE(decode_slave_frame(buf, &f));
        TEST_ASSERT_EQUAL_UINT32(batch * 10, f.first_frame);
        TEST_ASSERT_EQUAL(kFlagCounter, f.flags);
        b.on_frame_read();  // master reads it before the next pulse
    }
    TEST_ASSERT_EQUAL(0, b.overruns());
    TEST_ASSERT_EQUAL(0, b.realignments());
}

static void test_unread_frame_causes_overrun_flag() {
    SlaveBatcher b(kFlagCounter);
    uint8_t buf[32];
    for (int i = 0; i < 10; ++i) add(b, buf);  // frame 0..9 queued
    for (int i = 0; i < 10; ++i) TEST_ASSERT_EQUAL(0, add(b, buf));  // 10..19 dropped: not read
    TEST_ASSERT_EQUAL(1, b.overruns());
    b.on_frame_read();
    for (int i = 0; i < 9; ++i) add(b, buf);
    TEST_ASSERT_EQUAL(1, add(b, buf));
    SlaveFrame f;
    TEST_ASSERT_TRUE(decode_slave_frame(buf, &f));
    TEST_ASSERT_EQUAL_UINT32(20, f.first_frame);
    TEST_ASSERT_EQUAL(kFlagCounter | kFlagOverrun, f.flags);  // reported once...
    b.on_frame_read();
    for (int i = 0; i < 10; ++i) add(b, buf);
    TEST_ASSERT_TRUE(decode_slave_frame(buf, &f));
    TEST_ASSERT_EQUAL(kFlagCounter, f.flags);  // ...then cleared
}

static void test_read_mid_batch_realigns() {
    SlaveBatcher b(kFlagCounter);
    uint8_t buf[32];
    for (int i = 0; i < 14; ++i) add(b, buf);  // frame 0..9 queued, 10..13 in progress
    b.on_frame_read();                         // master read now: drop 10..13
    TEST_ASSERT_EQUAL(1, b.realignments());
    for (int i = 0; i < 9; ++i) TEST_ASSERT_EQUAL(0, add(b, buf));
    TEST_ASSERT_EQUAL(1, add(b, buf));
    SlaveFrame f;
    TEST_ASSERT_TRUE(decode_slave_frame(buf, &f));
    TEST_ASSERT_EQUAL_UINT32(14, f.first_frame);  // batch starts right after the read
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_counter_pattern_is_12_bit_sample_number);
    RUN_TEST(test_synthetic_in_range_and_bursts);
    RUN_TEST(test_frame_every_10_samples_when_read);
    RUN_TEST(test_unread_frame_causes_overrun_flag);
    RUN_TEST(test_read_mid_batch_realigns);
    return UNITY_END();
}
