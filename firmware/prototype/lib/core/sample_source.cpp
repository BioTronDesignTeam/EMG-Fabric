#include "sample_source.h"

namespace emg {

SampleSource::SampleSource(uint8_t mode, uint32_t seed) : mode_(mode), rng_(seed != 0 ? seed : 1u) {}

// 2000-sample (2 s) cycle: rest, ramp up, contraction, ramp down, rest.
int32_t SampleSource::synthetic_envelope(uint32_t n) {
    const int32_t rest = 40, peak = 1200;
    const int32_t t = static_cast<int32_t>(n % 2000);
    if (t < 800) return rest;
    if (t < 1000) return rest + (peak - rest) * (t - 800) / 200;
    if (t < 1600) return peak;
    if (t < 1800) return peak - (peak - rest) * (t - 1600) / 200;
    return rest;
}

// xorshift32: a tiny pseudo-random generator, good enough for fake noise.
// tiny and fast
uint32_t SampleSource::next_random() {
    uint32_t x = rng_;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    rng_ = x;
    return x;
}

int16_t SampleSource::read_sample(uint32_t n) {
    if (mode_ != kModeSynthetic) return counter_sample(n);

    // Integer math only
    // The sum of two uniform randoms (-65535..65535) looks more like real noise than a single one.
    // & 0xFFFF is just to keep the lowest 16 bits.
    const int32_t a = static_cast<int32_t>(next_random() & 0xFFFF);
    const int32_t b = static_cast<int32_t>(next_random() & 0xFFFF);
    int32_t v = 2048 + (a + b - 65535) * synthetic_envelope(n) / 65535;
    if (v < 0) v = 0;
    if (v > 4095) v = 4095;
    return static_cast<int16_t>(v);
}

}  // namespace emg
