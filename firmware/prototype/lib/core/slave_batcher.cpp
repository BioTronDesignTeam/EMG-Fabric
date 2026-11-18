#include "slave_batcher.h"

namespace emg {

void SlaveBatcher::on_frame_read() {
    frame_waiting_ = false;
    // If we are aligned, samples_in_batch_ should be 0, because slave hasn't collect anything yet before master read.
    // If we are misaligned, slave would've read >0 data already, we drop it and restart to be aligned.
    if (samples_in_batch_ > 0) {
        samples_in_batch_ = 0;
        ++realignments_;
    }
}

// adds a sample into the current batch. Returns true if batch is full + read to be queued in SPI.
bool SlaveBatcher::add_sample(int16_t sample, uint8_t out[kSpiFrameSize]) {
    batch_[samples_in_batch_++] = sample;
    ++next_sample_number_;
    if (samples_in_batch_ < kSamplesPerFrame) return false;

    samples_in_batch_ = 0;
    if (frame_waiting_) {
        // The previous frame is still waiting: the master missed a read. 
        // we can't replace a frame the driver already holds, so this batch is lost. 
        // Tell the master in the next frame
        report_overrun_ = true;
        ++overruns_;
        return false;
    }
    uint32_t first_sample_num = next_sample_number_ - kSamplesPerFrame;
    encode_slave_frame(mode_flags_ | (report_overrun_ ? kFlagOverrun : 0), first_sample_num, batch_, out);
    report_overrun_ = false;
    frame_waiting_ = true;
    return true;
}

}  // namespace emg
