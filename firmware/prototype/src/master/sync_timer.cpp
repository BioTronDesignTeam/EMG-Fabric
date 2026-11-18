#include "sync_timer.h"

#include <Arduino.h>

#include "config_master.h"
#include "esp_rom_sys.h"   // esp_rom_delay_us
#include "esp_timer.h"     // esp_timer_get_time
#include "soc/gpio_reg.h"  // GPIO_OUT_W1TS_REG / GPIO_OUT_W1TC_REG


// docs: 
// https://docs.espressif.com/projects/arduino-esp32/en/latest/api/timer.html

namespace {

hw_timer_t* s_timer = nullptr;
TaskHandle_t s_reader_task = nullptr;

// `volatile` tells the compiler the value can change outside the normal flow
// of the program (here, inside an interrupt), so it must re-read memory every
// time instead of keeping a cached copy in a register.
volatile uint32_t s_next_tick = 0;  // number of the NEXT pulse

// The tick and timestamp are two separate values that must always be read as
// a matching pair. A "critical section" (spinlock + interrupts off) stops the
// ISR from updating them while a task is half-way through reading them.
portMUX_TYPE s_edge_lock = portMUX_INITIALIZER_UNLOCKED;
SyncEdge s_last_batch_edge = {0, 0};

// ---- Interrupt service routine (ISR) -----------------------------------------
// The hardware timer calls this every 1 ms. Rules for ISRs:
//  * IRAM_ATTR puts the code in internal RAM. Code in flash cannot run while
//    flash is busy (e.g. being written), and a timer ISR could fire then.
//  * Keep it short; no Serial, no malloc, no blocking calls, no floats.
//  * Only use FreeRTOS functions that end in "FromISR".
//
// We busy-wait ~10 us for the pulse width. That is about 1% of the CPU and
// much simpler than setting up a second timer just to end the pulse.
void IRAM_ATTR on_sync_timer() {
    const int64_t now = esp_timer_get_time();
    // Direct register writes: one instruction each, and safe from IRAM.
    // W1TS = "write 1 to set", W1TC = "write 1 to clear" this pin's output.
    REG_WRITE(GPIO_OUT_W1TS_REG, 1u << kPinSync);
    esp_rom_delay_us(kSyncPulseUs);
    REG_WRITE(GPIO_OUT_W1TC_REG, 1u << kPinSync);

    const uint32_t tick = s_next_tick;  // the frame number of the pulse we just sent
    s_next_tick = tick + 1;

    if (tick % kFramesPerRead == kFramesPerRead - 1) {
        // This pulse completed a batch (frames tick-9 .. tick). Record it and
        // wake the SPI reader task.
        portENTER_CRITICAL_ISR(&s_edge_lock);
        s_last_batch_edge.tick = tick;
        s_last_batch_edge.time_us = now;
        portEXIT_CRITICAL_ISR(&s_edge_lock);

        // If the reader is still busy, the notification waits for it. The reader
        // clears all pending notifications at once (pdTRUE), so a late reader
        // runs once, on the newest edge, and never on a stale one.
        BaseType_t higher_prio_woken = pdFALSE;
        vTaskNotifyGiveFromISR(s_reader_task, &higher_prio_woken);

        if (higher_prio_woken) portYIELD_FROM_ISR();
    }
}

}  // namespace

void sync_timer_begin(TaskHandle_t reader_task) {
    s_reader_task = reader_task;
    pinMode(kPinSync, OUTPUT);
    digitalWrite(kPinSync, LOW);

    // Hardware timer 0. The 80 MHz APB clock / 80 = 1 MHz, so one count is
    // 1 us. The alarm fires every kSyncPeriodUs counts and auto-reloads.
    // A hardware timer keeps exact 1 ms spacing no matter what the CPU is
    // doing. A software delay loop would drift.
    s_timer = timerBegin(0, 80, true);
    timerAttachInterrupt(s_timer, &on_sync_timer, true); // links s_timer to the on_sync_timer task
    timerAlarmWrite(s_timer, kSyncPeriodUs, true); // trigger alarm every |kSyncPeriodUs|
    timerAlarmEnable(s_timer);
}

SyncEdge sync_timer_last_batch_edge() {
    portENTER_CRITICAL(&s_edge_lock);
    const SyncEdge e = s_last_batch_edge;
    portEXIT_CRITICAL(&s_edge_lock);
    return e;
}
