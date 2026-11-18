# protocol

The byte formats everyone agrees on. This is plain C++ with no Arduino or ESP32 code, so it runs on any board and in the laptop unit tests.

| File | What it does |
|---|---|
| `crc16.*` | CRC-16 checksum, used to catch corrupted bytes |
| `emg_bytes.h` | write and read numbers as little-endian bytes (`put_u32`, `get_u16`, …) |
| `spi_frames.*` | the 32-byte frame a slave sends to the master |
| `host_packet.*` | the packets between the master and the laptop, plus a parser that finds them in a byte stream |

The Python receiver (`Software/prototype/emg_protocol.py`) mirrors this folder. **If you change a format here, change it there too** and bump the version number.

## Examples

**CRC: is this data intact?**
```cpp
uint16_t crc = crc16_ccitt(data, len);                 // sender appends this
bool ok = crc16_ccitt(data, len) == received_crc;      // receiver checks it
```

**Bytes: put a number into a buffer, and get it back out**
```cpp
uint8_t buf[4];
put_u32(buf, 0x12345678);    // buf = 78 56 34 12
uint32_t v = get_u32(buf);   // 0x12345678
```

**SPI frame: the slave builds one, the master reads it**
```cpp
// slave
int16_t samples[kSamplesPerFrame] = {...};
uint8_t frame[kSpiFrameSize];
encode_slave_frame(kFlagCounter, first_frame, samples, frame);   // fills in magic, version, CRC

// master
SlaveFrame f;
if (decode_slave_frame(rx, &f)) {
    // f.first_frame, f.samples[0..9], f.flags
} // false = bad magic, version or CRC
```

**Host packet: send one, then find it again in a stream of bytes**
```cpp
// sender
uint8_t out[kHostMaxPacket];
size_t n = encode_host_packet(kPktLog, seq, (const uint8_t*)"hi", 2, out, sizeof(out));
Serial.write(out, n);

// receiver
HostPacketParser parser;
parser.feed(byte);                       // for each byte that arrives
HostPacket pkt;
while (parser.next(&pkt)) handle(pkt);   // complete, CRC-checked packets only
```
The parser skips junk such as boot text or half packets, and locks onto the next valid packet.

**Payloads: DATA and STATUS**
```cpp
DataPayload d = {};
d.tick = 1230;
d.slot_mask = 0b0001;                    // only slot 1 has data
d.slots[0] = {flags, first_frame, {...}};
uint8_t payload[kHostMaxPayload];
size_t n = build_data_payload(d, payload, sizeof(payload));
```

## Add a new packet type
1. Add a `kPktSomething` constant in `host_packet.h`.
2. Add the same constant in `emg_protocol.py`.
3. Send it with `host_send(kPktSomething, payload, len)` on the master.
