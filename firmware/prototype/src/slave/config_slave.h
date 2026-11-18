// config_slave.h - pins and settings for the SLAVE, in one place.
// Every slave runs identical firmware. The master tells them apart by which of
// its CS pins is wired to the slave's CS pin.
#pragma once

#include <stdint.h>

#include "driver/spi_slave.h"
#include "sdkconfig.h"
#include "spi_frames.h"

#if CONFIG_IDF_TARGET_ESP32S3
constexpr int kPinSck = 12;
constexpr int kPinMosi = 11;
constexpr int kPinMiso = 13;
constexpr int kPinCs = 10;
constexpr int kPinSync = 9;
constexpr spi_host_device_t kSpiHost = SPI2_HOST;
#else  // classic ESP32 (esp32dev)
constexpr int kPinSck = 18;
constexpr int kPinMosi = 23;
constexpr int kPinMiso = 19;
constexpr int kPinCs = 21;  // goes to master CS1, CS2, CS3 or CS4
constexpr int kPinSync = 22;
constexpr spi_host_device_t kSpiHost = SPI3_HOST;  // "VSPI"
#endif

// Same SPI mode as the master (mode 1; see config_master.h for why).
constexpr uint8_t kSpiMode = 1;

// What to sample: 1 = counter test pattern (default), 2 = synthetic EMG.
// Set with build_flags = -DSLAVE_MODE=2 in platformio.ini.
#ifndef SLAVE_MODE
#define SLAVE_MODE 1
#endif
constexpr uint8_t kMode = SLAVE_MODE;
static_assert(kMode == emg::kModeCounter || kMode == emg::kModeSynthetic, "SLAVE_MODE must be 1 or 2");

constexpr uint32_t kDebugBaud = 115200;  // the slave's own USB port: plain-text debug line
