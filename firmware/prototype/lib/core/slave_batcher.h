// slave_batcher.h - the slave's batching logic (portable).
//
// The slave collects one sample per SYNC pulse. After 10 samples it builds a
// 32-byte frame and queues it in its SPI driver, where it waits for the
// master to read it.
//
// How the batches line up with the master's reads (no handshake needed):
//   - The master reads just after every 10th SYNC pulse.
//   - When the slave notices a read, it starts a new batch.
//   - If a read arrives while a batch is partly full, the slave is out of
//     step: it drops those samples and starts fresh (a "realignment").
//
// Call order, once per SYNC pulse:
//   if (master read the queued frame) batcher.on_frame_read();
//   int16_t s = source.read_sample(batcher.next_sample_number());
//   if (batcher.add_sample(s, buf)) queue `buf` in the SPI driver;
#pragma once

#include <stdint.h>

#include "spi_frames.h"

namespace emg {

class SlaveBatcher {
public:
    SlaveBatcher(uint8_t mode_flags) : 
        mode_flags_(mode_flags), 
        samples_in_batch_(0), 
        next_sample_number_(0), 
        frame_waiting_(false), 
        report_overrun_(false), 
        overruns_(0), 
        realignments_(0) {}

    // The master has read (clocked out) the queued frame.
    void on_frame_read();

    // Number of the sample about to be taken (counts SYNC pulses since boot).
    uint32_t next_sample_number() const { return next_sample_number_; }

    // Add one sample. Returns true when `out` now holds a frame to queue.
    bool add_sample(int16_t sample, uint8_t out[kSpiFrameSize]);

    uint32_t overruns() const { return overruns_; }                // batches dropped (master too slow)
    uint32_t realignments() const { return realignments_; }  // partial batches dropped to realign

private:
    uint8_t mode_flags_;
    uint8_t samples_in_batch_;
    uint32_t next_sample_number_;  // counts SYNC pulses since boot
    bool frame_waiting_;           // in the SPI driver, for the master to read
    bool report_overrun_;          // set kFlagOverrun in the next frame
    int16_t batch_[kSamplesPerFrame];
    uint32_t overruns_;
    uint32_t realignments_;
};

}  // namespace emg
