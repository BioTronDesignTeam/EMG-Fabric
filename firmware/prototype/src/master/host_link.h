// host_link.h - binary packet link to the laptop over the USB serial port.
//
// RULE: nothing else may write to Serial on the master. Any stray text
// (Serial.print, printf, log_e) would land in the middle of the binary
// stream. Use host_log() instead: it sends a LOG packet.
#pragma once

#include <stdint.h>

#include "host_packet.h"

void host_link_begin();

// Encode and send one packet. Safe to call from several tasks: a mutex makes
// sure two packets never interleave on the wire. Do NOT call from an ISR.
void host_send(uint8_t type, const uint8_t* payload, uint16_t len);

// printf-style text, sent as a LOG packet.
void host_log(const char* fmt, ...) __attribute__((format(printf, 1, 2)));

// Read whatever bytes have arrived and return the next complete packet, if any.
bool host_poll(emg::HostPacket* out);
