// sync_timer.h - generates the 1 kHz SYNC pulse train with a hardware timer.
#pragma once

#include <stdint.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// When the master's slave read should happen: the tick (frame) number of the
// SYNC pulse that completed a batch, and when it was sent.
struct SyncEdge {
    uint32_t tick;     // frame number of that pulse (pulses are numbered 0, 1, 2, ...)
    int64_t time_us;   // esp_timer_get_time() at the rising edge
};

// Start SYNC. Every kFramesPerRead-th pulse wakes `reader_task` through a
// FreeRTOS task notification.
void sync_timer_begin(TaskHandle_t reader_task);

// The most recent batch-completing edge (safe to call from a task).
SyncEdge sync_timer_last_batch_edge();
