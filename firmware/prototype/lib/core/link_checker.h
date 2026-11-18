// link_checker.h - the master's bookkeeping for one slave slot (portable).
//
// Called once per read of the slot with the 32 bytes received and `tick`, the
// master pulse at which this read's samples[0] should have been taken.
//
// Guarantee: a frame is forwarded (Ok) only if its timing is proven, i.e.
// tick - first_frame equals the slot's locked offset. The offset is locked
// once two consecutive reads agree on it. Anything else is dropped (Skip):
// a stale frame after a master stall, the out-of-step frame after a slave
// boots or realigns.
//
// Counters: `gaps` = 10-sample batches this slot failed to deliver while
// connected; `crc_errors` = corrupted frames; `overruns` = frames the slave
// flagged as following a dropped batch.
#pragma once

#include <stdint.h>

#include "host_packet.h"  // SlotStatus
#include "spi_frames.h"

namespace emg {

enum class LinkResult : uint8_t {
    Ok,       // valid and on time: forward it
    Skip,     // valid, but its timing is not proven: drop it
    Invalid,  // bad magic/version/CRC, or nothing connected
};

class LinkChecker {
public:
    static constexpr uint32_t kAbsentAfterTicks = 1000;  // 1 s without a valid frame

    LinkChecker()
        : present_(false), locked_(false), have_candidate_(false), delivered_any_(false), locked_offset_(0),
          candidate_offset_(0), candidate_tick_(0), last_delivered_tick_(0), last_valid_tick_(0) {
        reset_stats();
    }

    LinkResult on_frame(const uint8_t* rx, uint32_t tick, SlaveFrame* out);

    bool present() const { return present_; }
    const SlotStatus& stats() const { return stats_; }
    void reset_stats();

private:
    void deliver(uint32_t tick, uint8_t flags);

    bool present_;
    bool locked_;
    bool have_candidate_;
    bool delivered_any_;
    uint32_t locked_offset_;  // tick - first_frame for on-time frames
    uint32_t candidate_offset_;
    uint32_t candidate_tick_;
    uint32_t last_delivered_tick_;
    uint32_t last_valid_tick_;
    SlotStatus stats_;
};

}  // namespace emg
