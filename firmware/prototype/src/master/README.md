# master

ESP32 firmware for the master. It sends the SYNC pulse, reads every slave every 10 ms, and streams the data to the laptop.

```
sync_timer  --every 10th pulse-->  spi_link  --DATA-->  host_link  --USB-->  laptop
                                                          ^
main.cpp loop(): STATUS every 1 s, laptop commands -------+
```

| File | What it does |
|---|---|
| `config_master.h` | **every pin and timing number.** Start here. |
| `sync_timer.*` | hardware timer: 10 µs SYNC pulse every 1 ms; wakes the reader on every 10th |
| `spi_link.*` | reader task (core 0): waits 200 µs, reads the 4 slots, checks them, sends one DATA packet |
| `host_link.*` | USB serial to the laptop: send packets, log text, receive commands |
| `main.cpp` | wires it all together; `loop()` sends STATUS and handles commands |

## Build and flash
```bash
pio run -e master -t upload --upload-port /dev/cu.usbserial-XXXX
python ../../../../Software/prototype/receiver.py /dev/cu.usbserial-XXXX
```
Don't open a serial monitor on the master. Its port carries binary packets that only `receiver.py` can read.

## Examples

**Print a message to the laptop.** Never use `Serial.print`: stray text would break the binary stream.
```cpp
host_log("slot %d connected", slot + 1);   // shows up in the receiver's log panel
```

**Add a laptop command** (in `main.cpp`):
```cpp
// host_packet.h: constexpr uint8_t kCmdMyThing = 2;
void handle_host_packet(const HostPacket& p) {
    if (p.type == kPktCmd && p.payload[0] == kCmdMyThing) { /* do it */ }
}
```

**Change a pin or the SPI speed** (in `config_master.h`):
```cpp
constexpr int kPinCs[kMaxSlots] = {21, 25, 26, 27};   // slot 1..4
constexpr int kSpiClockHz = 2000000;                   // try 2 MHz with long wires
```

## Rules
- **No slow work inside the read loop** (`read_all_slots`), such as logging or `delay`. It pushes later slots past the next pulse. Collect what you need and log after the loop.
- **All reads must finish within 1 ms of the pulse** (~90 µs per slot today).
- **Only `host_link` touches `Serial`.**
