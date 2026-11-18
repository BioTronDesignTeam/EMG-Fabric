// EMG prototype SLAVE (ESP32): makes up EMG samples and hands them to the master.
//
//   SYNC rising edge (1 kHz) --ISR wakes--> sample task
//   sample task: take 1 sample; every 10th, queue a 32-byte frame in the SPI driver
//   master reads the queued frame ~200 us later
//
// The slave's own USB port is not the data path. It only prints a debug line
// once per second (pio device monitor -e slave).
#include <Arduino.h>
#include <string.h>

#include "config_slave.h"
#include "esp_heap_caps.h"
#include "sample_source.h"
#include "slave_batcher.h"

using namespace emg;

namespace {

TaskHandle_t s_sample_task;
volatile uint32_t s_sync_edges = 0;  // `volatile`: changed by the ISR, so always re-read from memory

// The frame waiting for the master. The SPI hardware reads it by DMA (on
// its own, without the CPU), so it must be in DMA-capable RAM and 4-byte
// aligned. heap_caps_malloc(MALLOC_CAP_DMA) guarantees both. The batcher
// only writes here when no frame is queued, so the DMA never sees a
// half-written frame.
uint8_t* s_tx_frame;
spi_slave_transaction_t s_tx_trans;

SampleSource s_source(kMode);
SlaveBatcher s_batcher(mode_flags(kMode));

// ---- SYNC interrupt ------------------------------------------------------------
// An ISR (interrupt service routine) runs the moment the pin rises,
// interrupting whatever the CPU was doing, so it must be tiny. This one only
// wakes the sample task. The notification is a counter, so if the task is
// ever late, no pulse is lost: it handles each one in turn.
// IRAM_ATTR keeps the code in internal RAM, so it can run even while flash is busy.
void IRAM_ATTR on_sync() {
    s_sync_edges += 1;
    BaseType_t woke_higher_prio = pdFALSE;
    vTaskNotifyGiveFromISR(s_sample_task, &woke_higher_prio);
    if (woke_higher_prio) portYIELD_FROM_ISR();  // switch to the task right away
}

// ---- Sample task (runs once per SYNC pulse) ----------------------------------------
void sample_task(void*) {
    for (;;) {
        ulTaskNotifyTake(pdFALSE, portMAX_DELAY);  // wait for one SYNC pulse

        // 1. Did the master read our queued frame since the last pulse?
        //    (Timeout 0 = just check, don't wait.)
        spi_slave_transaction_t* done = nullptr;
        if (spi_slave_get_trans_result(kSpiHost, &done, 0) == ESP_OK) s_batcher.on_frame_read();

        // 2. Take this pulse's sample. Every 10th one completes a frame.
        const int16_t sample = s_source.read_sample(s_batcher.next_sample_number());
        if (!s_batcher.add_sample(sample, s_tx_frame)) continue;

        // 3. Hand the frame to the SPI driver. Nothing is sent yet: an SPI
        //    slave can't start a transfer. The frame waits until the master
        //    pulls our CS low and clocks it out.
        memset(&s_tx_trans, 0, sizeof(s_tx_trans));
        s_tx_trans.length = kSpiFrameSize * 8;  // in bits
        s_tx_trans.tx_buffer = s_tx_frame;
        if (spi_slave_queue_trans(kSpiHost, &s_tx_trans, 0) != ESP_OK) {
            s_batcher.on_frame_read();  // not queued after all; free the slot
        }
    }
}

void spi_begin() {
    spi_bus_config_t bus;
    memset(&bus, 0, sizeof(bus));
    bus.mosi_io_num = kPinMosi;
    bus.miso_io_num = kPinMiso;
    bus.sclk_io_num = kPinSck;
    bus.quadwp_io_num = -1;  // only used by quad-SPI flash chips
    bus.quadhd_io_num = -1;

    spi_slave_interface_config_t slv;
    memset(&slv, 0, sizeof(slv));
    slv.spics_io_num = kPinCs;
    slv.mode = kSpiMode;
    slv.queue_size = 1;  // at most one frame waiting

    ESP_ERROR_CHECK(spi_slave_initialize(kSpiHost, &bus, &slv, SPI_DMA_CH_AUTO));
    // Pull-up: if the CS wire is unplugged the pin stays high (= not selected)
    // instead of floating and triggering phantom reads.
    gpio_set_pull_mode(static_cast<gpio_num_t>(kPinCs), GPIO_PULLUP_ONLY);
}

}  // namespace

void setup() {
    Serial.begin(kDebugBaud);
    s_tx_frame = static_cast<uint8_t*>(heap_caps_malloc(kSpiFrameSize, MALLOC_CAP_DMA));
    spi_begin();

    // Seed from the chip's unique MAC so each slave makes different noise.
    const uint64_t mac = ESP.getEfuseMac();
    s_source = SampleSource(kMode, static_cast<uint32_t>(mac ^ (mac >> 32)));

    // Highest application priority: taking samples on time comes first.
    xTaskCreatePinnedToCore(sample_task, "sample", 4096, nullptr, configMAX_PRIORITIES - 2, &s_sample_task, 1);

    // Pull-down: an unplugged SYNC wire reads a clean 0 instead of random edges.
    pinMode(kPinSync, INPUT_PULLDOWN);
    attachInterrupt(digitalPinToInterrupt(kPinSync), on_sync, RISING);

    Serial.printf("\nslave boot: %s mode, SPI mode %u\n", kMode == kModeSynthetic ? "synthetic" : "counter",
                  kSpiMode);
}

void loop() {
    // Should grow by 1000 per second while SYNC is connected.
    Serial.printf("sync_edges=%lu samples=%lu overruns=%lu realigned=%lu\n",
                  static_cast<unsigned long>(s_sync_edges),
                  static_cast<unsigned long>(s_batcher.next_sample_number()),
                  static_cast<unsigned long>(s_batcher.overruns()),
                  static_cast<unsigned long>(s_batcher.realignments()));
    delay(1000);
}
