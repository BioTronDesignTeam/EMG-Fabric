#include "link_checker.h"

namespace emg {

void LinkChecker::reset_stats() {
    stats_.crc_errors = 0;
    stats_.gaps = 0;
    stats_.overruns = 0;
    stats_.last_flags = 0;
}

void LinkChecker::deliver(uint32_t tick, uint8_t flags) {
    if (delivered_any_) stats_.gaps += (tick - last_delivered_tick_) / kSamplesPerFrame - 1;
    last_delivered_tick_ = tick;
    delivered_any_ = true;
    if (flags & kFlagOverrun) ++stats_.overruns;
}

LinkResult LinkChecker::on_frame(const uint8_t* rx, uint32_t tick, SlaveFrame* out) {
    // invalid frame: 
    if (!decode_slave_frame(rx, out)) {
        if (present_) {
            ++stats_.crc_errors;
            if (tick - last_valid_tick_ >= kAbsentAfterTicks) present_ = false;
        }
        return LinkResult::Invalid;
    }

    last_valid_tick_ = tick;
    stats_.last_flags = out->flags;
    const uint32_t offset = tick - out->first_frame;

    if (!present_) { // if slave wasn't present previously, it is now.
        present_ = true;
        locked_ = false;
        delivered_any_ = false;
    } else if (locked_ && offset == locked_offset_) {
        deliver(tick, out->flags);
        return LinkResult::Ok;
    } else if (have_candidate_ && offset == candidate_offset_ && tick == candidate_tick_ + kSamplesPerFrame) {
        locked_ = true;
        locked_offset_ = offset;
        have_candidate_ = false;
        deliver(tick, out->flags);
        return LinkResult::Ok;
    }

    have_candidate_ = true;
    candidate_offset_ = offset;
    candidate_tick_ = tick;
    return LinkResult::Skip;
}

}  // namespace emg
