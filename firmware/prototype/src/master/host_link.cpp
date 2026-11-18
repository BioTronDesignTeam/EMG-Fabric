#include "host_link.h"

#include <Arduino.h>
#include <stdarg.h>
#include <stdio.h>

#include "config_master.h"

namespace {
SemaphoreHandle_t s_send_lock;  // protects s_next_seq and the order of bytes on the wire
uint16_t s_next_seq = 0;
emg::HostPacketParser s_parser;
}  // namespace

void host_link_begin() {
    s_send_lock = xSemaphoreCreateMutex();
    // Larger buffers absorb bursts. Average traffic is only ~4 KB/s against
    // ~92 KB/s of link capacity. These must be set before begin().
    Serial.setTxBufferSize(2048);
    Serial.setRxBufferSize(512);
    Serial.begin(kHostBaud);
}

void host_send(uint8_t type, const uint8_t* payload, uint16_t len) {
    uint8_t buf[emg::kHostMaxPacket];
    xSemaphoreTake(s_send_lock, portMAX_DELAY);
    const size_t n = emg::encode_host_packet(type, s_next_seq, payload, len, buf, sizeof(buf));
    if (n > 0) {
        ++s_next_seq;
        Serial.write(buf, n);
    }
    xSemaphoreGive(s_send_lock);
}

void host_log(const char* fmt, ...) {
    char text[200];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(text, sizeof(text), fmt, ap);
    va_end(ap);
    if (n < 0) return;
    if (n >= static_cast<int>(sizeof(text))) n = sizeof(text) - 1;  // truncated
    host_send(emg::kPktLog, reinterpret_cast<const uint8_t*>(text), static_cast<uint16_t>(n));
}

bool host_poll(emg::HostPacket* out) {
    // Return any packet already complete before reading more bytes.
    if (s_parser.next(out)) return true;
    while (Serial.available() > 0) {
        s_parser.feed(static_cast<uint8_t>(Serial.read()));
        if (s_parser.next(out)) return true;
    }
    return false;
}
