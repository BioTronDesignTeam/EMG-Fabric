// config_master.h - every pin and timing constant for the master
#pragma once

#include <stdint.h>

#include "driver/spi_master.h"
#include "sdkconfig.h"
#include "host_packet.h"  // kMaxSlots

// ---- Pins -------------------------------------------------------------------
// ESP32 specific for now, needs to be changed if we are using another board!
// Avoids the ESP32 strapping pins (0, 2, 5, 12, 15) and input-only pins (34-39).
// SCK/MOSI/MISO/SYNC are shared by all slaves; each slave has its own CS.
// GPIO 4, 13, 32, 33 are left free for a future "flash the slaves" feature.
#if CONFIG_IDF_TARGET_ESP32S3
constexpr int kPinSck = 12;
constexpr int kPinMosi = 11;
constexpr int kPinMiso = 13;
constexpr int kPinSync = 9;
constexpr int kPinCs[emg::kMaxSlots] = {10, 14, 15, 16};
constexpr spi_host_device_t kSpiHost = SPI2_HOST;
#else  // classic ESP32 (esp32dev)
constexpr int kPinSck = 18;
constexpr int kPinMosi = 23;  // nothing is sent to the slaves yet; kept wired for later
constexpr int kPinMiso = 19;
constexpr int kPinSync = 22;
constexpr int kPinCs[emg::kMaxSlots] = {21, 25, 26, 27};  // slot 1, 2, 3, 4
constexpr spi_host_device_t kSpiHost = SPI3_HOST;          // "VSPI"
#endif

// The SYNC ISR writes the GPIO register directly, which covers pins 0-31.
static_assert(kPinSync < 32, "SYNC pin must be GPIO0..31");

// ---- SPI --------------------------------------------------------------------
// 4 MHz: one 32-byte read takes ~64 us plus overhead (~100 us total). All 4
// slots must be read inside the 1 ms gap before the next SYNC pulse. Drop to
// 2 MHz if long wires cause CRC errors.
constexpr int kSpiClockHz = 4000000;
// SPI mode 1 (not 0): the ESP32 SPI slave with DMA changes its output half a
// clock early in modes 0 and 2 (ESP-IDF "SPI Slave: Restrictions and Known
// Issues"). Both sides must use the same mode.
constexpr uint8_t kSpiMode = 1;

// ---- Timing -----------------------------------------------------------------
constexpr uint32_t kSyncPeriodUs = 1000;  // 1 kHz sampling
constexpr uint32_t kSyncPulseUs = 10;
constexpr uint32_t kFramesPerRead = 10;   // read the slaves after every 10th pulse
constexpr uint32_t kReadDelayUs = 200;    // time for slaves to queue their frame

// ---- Laptop link ------------------------------------------------------------
constexpr uint32_t kHostBaud = 921600;
constexpr uint32_t kStatusPeriodMs = 1000;
