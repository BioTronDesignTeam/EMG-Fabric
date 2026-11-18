// sample_source.h - where the slave's samples come from (portable).
//
// There is no EMG sensor yet, so samples are made up. read_sample() is the one
// place a real ADC (e.g. the ADS1299) will plug in later.
#pragma once

#include <stdint.h>

#include "spi_frames.h"

namespace emg {

class SampleSource {
public:
    explicit SampleSource(uint8_t mode = kModeCounter, uint32_t seed = 0x2545F491u);

    // The sample for SYNC pulse number `n` (counted by the slave since boot).
    int16_t read_sample(uint32_t n);

    // Counter test pattern: the sample IS its number, 12 bits wide (like a
    // 12-bit ADC). The laptop knows exactly what to expect, so any lost,
    // repeated or reordered sample shows up.
    static int16_t counter_sample(uint32_t n) { return static_cast<int16_t>(n & 0x0FFF); }

    // Synthetic EMG: noise around 2048 whose loudness rises and falls in a
    // 2-second cycle, like a muscle contracting and relaxing.
    static int32_t synthetic_envelope(uint32_t n);

private:
    uint32_t next_random();
    uint8_t mode_;
    uint32_t rng_;
};

}  // namespace emg
