// EMG prototype MASTER (ESP32).
//
//   hardware timer --1 kHz--> SYNC pin ---------------------------> all slaves
//        | every 10th pulse wakes
//        v
//   spi_link task: 200 us later, read slots 1-4 (32 bytes each)
//        | one DATA packet per 10 ms with every connected slave
//        v
//   USB serial (921600 baud, binary packets only) --> laptop (receiver.py)
//
// loop() sends a STATUS packet every second and handles the laptop's commands.
#include <Arduino.h>
#include <string.h>

#include "config_master.h"
#include "esp_log.h"
#include "host_link.h"
#include "spi_link.h"
#include "sync_timer.h"

using namespace emg;

namespace {

uint32_t s_last_status_ms = 0;

void send_status() {
    StatusPayload s;
    memset(&s, 0, sizeof(s));
    s.uptime_ms = millis();
    spi_link_get_status(&s);
    uint8_t payload[kHostMaxPayload];
    const size_t n = build_status_payload(s, payload, sizeof(payload));
    host_send(kPktStatus, payload, static_cast<uint16_t>(n));
}

void handle_host_packet(const HostPacket& p) {
    if (p.type == kPktCmd && p.len >= 1 && p.payload[0] == kCmdResetStats) {
        spi_link_reset_stats();
        host_log("stats reset");
    } else {
        host_log("unknown packet from laptop (type 0x%02x)", p.type);
    }
}

}  // namespace

void setup() {
    // Silence ESP-IDF's own log text: it would corrupt our binary serial
    // stream. Our messages go out as LOG packets instead.
    esp_log_level_set("*", ESP_LOG_NONE);

    host_link_begin(); // laptop <--> master comms

    // spi_link_begin() is the reader task that gets the data from slaves
    sync_timer_begin(spi_link_begin()); // master <--> slave sync timer + comms

    host_log("master boot: 4 slots, SPI mode %u @ %d Hz, 1 kHz sampling", kSpiMode, kSpiClockHz);
}

void loop() {
    HostPacket p;
    while (host_poll(&p)) handle_host_packet(p); // instr from laptop receiver software

    const uint32_t now = millis();
    if (now - s_last_status_ms >= kStatusPeriodMs) { // status packet to receiver each second
        s_last_status_ms = now;
        send_status();
    }
    vTaskDelay(1);  // sleep 1 ms so other tasks get the CPU
}
