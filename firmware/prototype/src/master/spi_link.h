// spi_link.h - reads all slave slots every 10 ms and sends DATA packets to the laptop.
#pragma once

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "host_packet.h"

// Set up SPI and start the reader task. Returns the task handle, which the
// SYNC timer needs so it can wake the task.
TaskHandle_t spi_link_begin();

// Copy the per-slot counters (for the STATUS packet).
void spi_link_get_status(emg::StatusPayload* out);

void spi_link_reset_stats();
