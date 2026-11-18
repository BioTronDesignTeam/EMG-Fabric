// Master side: one slot's validity, timing lock, connect/disconnect and counters.
#include <string.h>
#include <unity.h>

#include "link_checker.h"

using namespace emg;

void setUp() {}
void tearDown() {}

static LinkResult feed(LinkChecker& lc, uint32_t tick, uint32_t first, uint8_t flags = kFlagCounter) {
    uint8_t rx[32];
    int16_t s[10] = {0};
    encode_slave_frame(flags, first, s, rx);
    SlaveFrame f;
    return lc.on_frame(rx, tick, &f);
}

static LinkResult feed_garbage(LinkChecker& lc, uint32_t tick) {
    uint8_t rx[32];
    memset(rx, 0xFF, sizeof(rx));
    SlaveFrame f;
    return lc.on_frame(rx, tick, &f);
}

// Connects a slave whose sample n is taken at master pulse n + 96, delivering tick 120.
static void lock_at_96(LinkChecker& lc) {
    TEST_ASSERT_TRUE(feed(lc, 100, 5) == LinkResult::Skip);   // out-of-step boot frame
    TEST_ASSERT_TRUE(feed(lc, 110, 14) == LinkResult::Skip);  // first aligned frame: candidate
    TEST_ASSERT_TRUE(feed(lc, 120, 24) == LinkResult::Ok);    // confirmed: locked
}

static void test_empty_slot_is_absent_and_counts_nothing() {
    LinkChecker lc;
    for (uint32_t t = 0; t < 5000; t += 10) TEST_ASSERT_TRUE(feed_garbage(lc, t) == LinkResult::Invalid);
    TEST_ASSERT_FALSE(lc.present());
    TEST_ASSERT_EQUAL(0, lc.stats().crc_errors);
}

static void test_locks_after_two_consistent_frames() {
    LinkChecker lc;
    lock_at_96(lc);
    TEST_ASSERT_TRUE(lc.present());
    for (uint32_t k = 1; k <= 5; ++k) TEST_ASSERT_TRUE(feed(lc, 120 + 10 * k, 24 + 10 * k) == LinkResult::Ok);
    TEST_ASSERT_EQUAL(0, lc.stats().gaps);
}

static void test_stale_frame_after_master_stall_is_dropped() {
    LinkChecker lc;
    lock_at_96(lc);
    TEST_ASSERT_TRUE(feed(lc, 130, 34) == LinkResult::Ok);
    // Master misses reads at 140 and 150. At 160 it gets the frame the slave
    // queued for 140: right samples, wrong time.
    TEST_ASSERT_TRUE(feed(lc, 160, 44) == LinkResult::Skip);
    TEST_ASSERT_TRUE(feed(lc, 170, 74) == LinkResult::Ok);
    TEST_ASSERT_EQUAL(3, lc.stats().gaps);  // ticks 140, 150, 160 never delivered
}

static void test_two_stale_frames_never_lock_a_wrong_offset() {
    LinkChecker lc;
    lock_at_96(lc);
    TEST_ASSERT_TRUE(feed(lc, 140, 34) == LinkResult::Skip);  // stale by 10
    TEST_ASSERT_TRUE(feed(lc, 160, 54) == LinkResult::Skip);  // stale by 10 again, after another miss
    TEST_ASSERT_TRUE(feed(lc, 170, 74) == LinkResult::Ok);    // still the original offset
}

static void test_crc_error_counts_as_gap() {
    LinkChecker lc;
    lock_at_96(lc);
    uint8_t rx[32];
    int16_t s[10] = {0};
    encode_slave_frame(kFlagCounter, 34, s, rx);
    rx[10] ^= 1;
    SlaveFrame f;
    TEST_ASSERT_TRUE(lc.on_frame(rx, 130, &f) == LinkResult::Invalid);
    TEST_ASSERT_TRUE(feed(lc, 140, 44) == LinkResult::Ok);
    TEST_ASSERT_EQUAL(1, lc.stats().crc_errors);
    TEST_ASSERT_EQUAL(1, lc.stats().gaps);
}

static void test_disconnect_and_reconnect() {
    LinkChecker lc;
    lock_at_96(lc);
    uint32_t t = 130;
    for (; t < 130 + LinkChecker::kAbsentAfterTicks; t += 10) feed_garbage(lc, t);
    TEST_ASSERT_FALSE(lc.present());

    TEST_ASSERT_TRUE(feed(lc, t, 3) == LinkResult::Skip);
    TEST_ASSERT_TRUE(feed(lc, t + 10, 11) == LinkResult::Skip);
    TEST_ASSERT_TRUE(feed(lc, t + 20, 21) == LinkResult::Ok);
    TEST_ASSERT_EQUAL(0, lc.stats().gaps);  // time spent disconnected is not a gap
}

static void test_slave_reboot_relocks() {
    LinkChecker lc;
    lock_at_96(lc);
    TEST_ASSERT_TRUE(feed(lc, 130, 34) == LinkResult::Ok);
    // The slave restarts its count from 0 within a second, so it never looks disconnected.
    TEST_ASSERT_TRUE(feed(lc, 140, 3) == LinkResult::Skip);
    TEST_ASSERT_TRUE(feed(lc, 150, 11) == LinkResult::Skip);
    TEST_ASSERT_TRUE(feed(lc, 160, 21) == LinkResult::Ok);
    TEST_ASSERT_TRUE(feed(lc, 170, 31) == LinkResult::Ok);
    TEST_ASSERT_EQUAL(2, lc.stats().gaps);
}

static void test_overrun_counted_and_reset() {
    LinkChecker lc;
    lock_at_96(lc);
    feed(lc, 130, 34, kFlagCounter | kFlagOverrun);
    TEST_ASSERT_EQUAL(1, lc.stats().overruns);
    TEST_ASSERT_EQUAL(kFlagCounter | kFlagOverrun, lc.stats().last_flags);
    lc.reset_stats();
    TEST_ASSERT_EQUAL(0, lc.stats().overruns);
    TEST_ASSERT_TRUE(lc.present());
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_empty_slot_is_absent_and_counts_nothing);
    RUN_TEST(test_locks_after_two_consistent_frames);
    RUN_TEST(test_stale_frame_after_master_stall_is_dropped);
    RUN_TEST(test_two_stale_frames_never_lock_a_wrong_offset);
    RUN_TEST(test_crc_error_counts_as_gap);
    RUN_TEST(test_disconnect_and_reconnect);
    RUN_TEST(test_slave_reboot_relocks);
    RUN_TEST(test_overrun_counted_and_reset);
    return UNITY_END();
}
