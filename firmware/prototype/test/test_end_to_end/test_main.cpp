// End-to-end simulation of the timing logic, with no hardware:
// 4 slaves that boot at different moments, a master that pulses SYNC 1000
// times a second and reads every slot after each 10th pulse. Checks that the
// slaves line up with the master's reads by themselves, that no data is lost
// or repeated, and that samples from different slaves line up in time.
#include <string.h>
#include <unity.h>

#include "link_checker.h"
#include "sample_source.h"
#include "slave_batcher.h"

using namespace emg;

void setUp() {}
void tearDown() {}

// One simulated slave: the same calls src/slave/main.cpp makes.
struct SimSlave {
    SimSlave() : boot_pulse(0), batcher(kFlagCounter), queued(false), read_since_last_pulse(false) {}
    uint32_t boot_pulse;  // master pulse number at which this slave started
    SampleSource source;
    SlaveBatcher batcher;
    uint8_t tx[32];
    bool queued;
    bool read_since_last_pulse;

    void on_sync() {
        if (read_since_last_pulse) {
            batcher.on_frame_read();
            read_since_last_pulse = false;
        }
        const int16_t s = source.read_sample(batcher.next_sample_number());
        if (batcher.add_sample(s, tx)) queued = true;
    }
    // Master clocks 32 bytes out of this slave.
    void master_reads(uint8_t rx[32]) {
        if (!queued) {
            memset(rx, 0xFF, 32);  // nothing queued: the master reads garbage
            return;
        }
        memcpy(rx, tx, 32);
        queued = false;
        read_since_last_pulse = true;
    }
};

struct Result {
    uint32_t ok_frames[4];
    uint32_t bad_samples;
    bool aligned;
};

// The master skips its reads at pulses in [skip_from, skip_to) (a master stall).
static Result run(const uint32_t boot[4], uint32_t pulses, uint32_t skip_from, uint32_t skip_to, LinkChecker* lc) {
    SimSlave slaves[4];
    for (int s = 0; s < 4; ++s) slaves[s].boot_pulse = boot[s];
    Result res;
    memset(&res, 0, sizeof(res));
    res.aligned = true;
    int64_t offset[4] = {0, 0, 0, 0};
    bool have_offset[4] = {false, false, false, false};

    for (uint32_t tick = 0; tick < pulses; ++tick) {
        for (int s = 0; s < 4; ++s) {
            if (tick >= slaves[s].boot_pulse) slaves[s].on_sync();
        }
        if (tick % 10 != 9) continue;
        if (tick >= skip_from && tick < skip_to) continue;
        const uint32_t data_tick = tick - 9;  // what the master puts in DATA
        for (int s = 0; s < 4; ++s) {
            uint8_t rx[32];
            slaves[s].master_reads(rx);
            SlaveFrame f;
            if (lc[s].on_frame(rx, data_tick, &f) != LinkResult::Ok) continue;
            ++res.ok_frames[s];
            for (int i = 0; i < 10; ++i) {
                if (f.samples[i] != SampleSource::counter_sample(f.first_frame + i)) ++res.bad_samples;
            }
            // The slave's sample k is taken at master pulse boot + k. So for
            // correct timing, first_frame + boot must equal data_tick in every
            // forwarded frame.
            const int64_t off = static_cast<int64_t>(data_tick) - f.first_frame;
            if (!have_offset[s]) {
                offset[s] = off;
                have_offset[s] = true;
            }
            if (off != offset[s] || off != static_cast<int64_t>(slaves[s].boot_pulse)) res.aligned = false;
        }
    }
    return res;
}

static void test_slaves_booting_at_different_times_line_up() {
    const uint32_t boot[4] = {0, 3, 27, 1234};  // arbitrary moments, not multiples of 10
    LinkChecker lc[4];
    const Result r = run(boot, 60000, 0, 0, lc);  // one minute
    for (int s = 0; s < 4; ++s) {
        TEST_ASSERT_TRUE(lc[s].present());
        TEST_ASSERT_EQUAL(0, lc[s].stats().gaps);
        TEST_ASSERT_EQUAL(0, lc[s].stats().crc_errors);
        TEST_ASSERT_EQUAL(0, lc[s].stats().overruns);
        // ~1 frame per 10 ms after the slave boots (slot 4 boots 1.2 s late).
        TEST_ASSERT_TRUE(r.ok_frames[s] >= (60000 - boot[s]) / 10 - 3);
    }
    TEST_ASSERT_EQUAL(0, r.bad_samples);
    TEST_ASSERT_TRUE(r.aligned);
}

static void test_missed_read_is_counted_and_timing_stays_correct() {
    const uint32_t boot[4] = {0, 5, 11, 2};
    LinkChecker lc[4];
    const Result r = run(boot, 10000, 5009, 5010, lc);  // master skips the read after pulse 5009
    for (int s = 0; s < 4; ++s) {
        TEST_ASSERT_EQUAL(1, lc[s].stats().overruns);
        TEST_ASSERT_EQUAL(2, lc[s].stats().gaps);  // the missed batch + the stale one dropped
    }
    TEST_ASSERT_EQUAL(0, r.bad_samples);
    TEST_ASSERT_TRUE(r.aligned);
}

static void test_long_stall_is_counted_exactly() {
    const uint32_t boot[4] = {0, 5, 11, 2};
    LinkChecker lc[4];
    const Result r = run(boot, 10000, 5009, 5509, lc);  // 50 reads missed
    for (int s = 0; s < 4; ++s) {
        TEST_ASSERT_TRUE(lc[s].present());
        TEST_ASSERT_EQUAL(51, lc[s].stats().gaps);  // 50 missed + 1 stale dropped
    }
    TEST_ASSERT_EQUAL(0, r.bad_samples);
    TEST_ASSERT_TRUE(r.aligned);
}

int main() {
    UNITY_BEGIN();
    RUN_TEST(test_slaves_booting_at_different_times_line_up);
    RUN_TEST(test_missed_read_is_counted_and_timing_stays_correct);
    RUN_TEST(test_long_stall_is_counted_exactly);
    return UNITY_END();
}
