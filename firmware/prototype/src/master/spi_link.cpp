#include "spi_link.h"

#include <Arduino.h>
#include <string.h>

#include "config_master.h"
#include "esp_heap_caps.h"
#include "esp_timer.h"
#include "host_link.h"
#include "link_checker.h"
#include "sync_timer.h"

using namespace emg;

namespace {

// The ESP32 drives at most 3 CS pins in hardware, so we drive them ourselves.
spi_device_handle_t s_spi;

// Receive buffer for the SPI DMA. DMA lets the SPI hardware write straight
// into RAM without the CPU copying each byte. It can only reach certain RAM
// and needs 4-byte alignment, which MALLOC_CAP_DMA guarantees.
uint8_t* s_rx_frame;

// Shared with loop() (STATUS, reset); protected by s_checkers_lock.
SemaphoreHandle_t s_checkers_lock;
LinkChecker s_checkers[kMaxSlots];

// Read one slot: 32 bytes in. Nothing goes out (tx_buffer = nullptr).
void read_slot(int slot) {
    spi_transaction_t t;
    memset(&t, 0, sizeof(t));
    t.length = kSpiFrameSize * 8;  // in bits
    t.rx_buffer = s_rx_frame;
    memset(s_rx_frame, 0, kSpiFrameSize);
    digitalWrite(kPinCs[slot], LOW);
    spi_device_polling_transmit(s_spi, &t);
    digitalWrite(kPinCs[slot], HIGH);
}

void read_all_slots(const SyncEdge& edge) {
    DataPayload d;
    memset(&d, 0, sizeof(d));
    d.tick = edge.tick - (kFramesPerRead - 1);  // master pulse number of samples[0]

    // Logged after the loop: logging is slow and must never delay a read.
    uint8_t connected = 0, disconnected = 0;

    for (int slot = 0; slot < static_cast<int>(kMaxSlots); ++slot) {
        read_slot(slot);

        SlaveFrame f;
        xSemaphoreTake(s_checkers_lock, portMAX_DELAY);
        const bool was_present = s_checkers[slot].present();
        const LinkResult r = s_checkers[slot].on_frame(s_rx_frame, d.tick, &f);
        const bool is_present = s_checkers[slot].present();
        xSemaphoreGive(s_checkers_lock);

        if (r == LinkResult::Ok) {
            d.slot_mask |= 1u << slot;
            d.slots[slot].flags = f.flags;
            d.slots[slot].first_frame = f.first_frame;
            memcpy(d.slots[slot].samples, f.samples, sizeof(f.samples));
        }
        if (is_present && !was_present) connected |= 1u << slot;
        if (!is_present && was_present) disconnected |= 1u << slot;
    }

    // Sent even with no slots, so the laptop sees one DATA tick every 10 ms.
    uint8_t payload[kHostMaxPayload];
    const size_t n = build_data_payload(d, payload, sizeof(payload));
    host_send(kPktData, payload, static_cast<uint16_t>(n));

    for (int slot = 0; slot < static_cast<int>(kMaxSlots); ++slot) {
        if (connected & (1u << slot)) host_log("slot %d connected", slot + 1);
        if (disconnected & (1u << slot)) host_log("slot %d disconnected", slot + 1);
    }
}

// The reader task. A FreeRTOS task is like a thread: it may block and use
// drivers, unlike an interrupt handler.
void spi_task(void*) {
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);  // sleep until the 10th SYNC pulse
        const SyncEdge edge = sync_timer_last_batch_edge();

        // Give the slaves ~200 us to take their 10th sample and queue the
        // frame. vTaskDelay can't wait less than 1 ms, so busy-wait.
        while (esp_timer_get_time() < edge.time_us + kReadDelayUs) {
        }
        read_all_slots(edge);
    }
}

}  // namespace

TaskHandle_t spi_link_begin() {
    s_checkers_lock = xSemaphoreCreateMutex();
    s_rx_frame = static_cast<uint8_t*>(heap_caps_malloc(kSpiFrameSize, MALLOC_CAP_DMA));

    spi_bus_config_t bus;
    memset(&bus, 0, sizeof(bus));
    bus.mosi_io_num = kPinMosi;
    bus.miso_io_num = kPinMiso;
    bus.sclk_io_num = kPinSck;
    bus.quadwp_io_num = -1;  // only used by quad-SPI flash chips
    bus.quadhd_io_num = -1;
    bus.max_transfer_sz = kSpiFrameSize;
    ESP_ERROR_CHECK(spi_bus_initialize(kSpiHost, &bus, SPI_DMA_CH_AUTO));

    // HIGH before OUTPUT: otherwise CS briefly goes LOW, which a slave sees as a read.
    for (int pin : kPinCs) {
        digitalWrite(pin, HIGH);
        pinMode(pin, OUTPUT);
    }
    spi_device_interface_config_t dev;
    memset(&dev, 0, sizeof(dev));
    dev.mode = kSpiMode;
    dev.clock_speed_hz = kSpiClockHz;
    dev.spics_io_num = -1;
    dev.queue_size = 1;
    ESP_ERROR_CHECK(spi_bus_add_device(kSpiHost, &dev, &s_spi));

    // High priority, on core 0. Arduino's loop() runs on core 1, so laptop
    // traffic never delays a read.
    TaskHandle_t task;
    xTaskCreatePinnedToCore(spi_task, "spi_link", 4096, nullptr, configMAX_PRIORITIES - 2, &task, 0);
    return task;
}

void spi_link_get_status(StatusPayload* out) {
    xSemaphoreTake(s_checkers_lock, portMAX_DELAY);
    out->present_mask = 0;
    for (size_t slot = 0; slot < kMaxSlots; ++slot) {
        if (s_checkers[slot].present()) out->present_mask |= 1u << slot;
        out->slots[slot] = s_checkers[slot].stats();
    }
    xSemaphoreGive(s_checkers_lock);
}

void spi_link_reset_stats() {
    xSemaphoreTake(s_checkers_lock, portMAX_DELAY);
    for (size_t slot = 0; slot < kMaxSlots; ++slot) s_checkers[slot].reset_stats();
    xSemaphoreGive(s_checkers_lock);
}
