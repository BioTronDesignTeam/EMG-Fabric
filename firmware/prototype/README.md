# EMG armband prototype firmware

One ESP32 **master** and 0–4 ESP32 **slaves**. The slaves sample at 1 kHz and the master collects their samples and streams them to a laptop over USB.

```
              SYNC (1 kHz pulse) ───────────────────────────► every slave
 MASTER  ◄── SPI: 32 bytes from each slave every 10 ms ──────  slaves 1–4
   │
   │ USB serial, 921600 baud, binary packets
   ▼
 laptop: Software/prototype/receiver.py
```

There is no EMG sensor yet, so the slaves make up their samples. The default is a **counter test pattern**: each sample equals its own sample number, so the laptop can verify that nothing was lost or repeated. With `-DSLAVE_MODE=2` they produce **synthetic EMG** instead, noise bursts that look like muscle contractions.

## 1. Wiring

| Signal | Master GPIO | Each slave's GPIO | Shared? |
|--------|-------------|-------------------|---------|
| SCK  | 18 | 18 | all slaves |
| MISO | 19 | 19 | all slaves |
| MOSI | 23 | 23 | all slaves (unused for now; wire it anyway) |
| SYNC | 22 | 22 | all slaves |
| CS   | **21** → slave 1, **25** → slave 2, **26** → slave 3, **27** → slave 4 | 21 | one wire per slave |
| GND  | GND | GND | all boards. **Always connect it.** |

* Every slave runs **the same firmware**. Which master CS pin it's wired to decides whether it's slave 1, 2, 3 or 4.
* Connect any number of slaves (0–4) to any of the CS pins. The master detects them on its own.
* Keep the wires short (under ~20 cm). SPI runs at 4 MHz.
* Power: the master runs from the laptop's USB. The slaves can each use their own USB cable, or share one supply (e.g. a power bank into slave 1, its VIN wired to the other slaves' VIN). GND is always shared.
* The pins avoid the ESP32's strapping pins (0, 2, 5, 12, 15) and its input-only pins (34–39). GPIO 4, 13, 32 and 33 are kept free for future use. All pins are set in `src/master/config_master.h` and `src/slave/config_slave.h`.

## 2. Build and flash

You need PlatformIO: the **PlatformIO IDE** extension in VS Code (open the folder `firmware/prototype` itself, not the repo root), or `pip install platformio`.

```bash
cd EMG-Fabric/firmware/prototype
pio run -e master -t upload --upload-port <MASTER_PORT>
pio run -e slave  -t upload --upload-port <SLAVE_PORT>    # repeat for each slave
pio test -e native                                         # unit tests, no hardware needed
```

* `pio device list` shows the ports. On macOS they look like `/dev/cu.usbserial-0001`, on Windows `COM5`.
* If an upload hangs at `Connecting....`, hold the board's **BOOT** button.
* **Synthetic EMG instead of the counter pattern:** uncomment `; build_flags = ... -DSLAVE_MODE=2` under `[env:slave]` in `platformio.ini`, then reflash the slaves.
* **Different board:** change `board = esp32dev` in `platformio.ini` (one place). ESP32-S3 pins are set up but not tested.

Optional: each slave prints a debug line once per second on its own USB port:

```bash
pio device monitor -e slave --port <SLAVE_PORT>
# sync_edges=53000 samples=53000 overruns=0 realigned=1
```

`sync_edges` should grow by 1000 per second. Never open a monitor on the **master**: its port carries binary data that only `receiver.py` can read.

## 3. Run

```bash
cd EMG-Fabric/Software/prototype
pip install -r requirements.txt
python receiver.py <MASTER_PORT>
```

```
  101 pkt/s   2000 samples/s   usb crc 0   lost 0   seq jumps 0   missed ticks 0
  slot  state      mode     crc errors  gaps  overruns  counter check
  1     ● present  counter           0     0         0  PASS 4,200/4,200
  2     ● present  counter           0     0         0  PASS 4,200/4,200
  3     ○ absent
  4     ○ absent
```

## 4. Testing checklist

These are one-time checks when you first wire things up. Do them in order, so that if something fails you know which part to look at.

1. **One slave.** Wire slave 1 only and run the receiver. You should see `slot 1 connected` in the log panel, about 1000 samples/s, `counter check PASS`, and `gaps=0`.
   If nothing connects, check GND, MISO, SCK and CS. If `sync_edges` on the slave stays at 0, check the SYNC wire.
2. **Unplug and replug.** Pull slave 1's CS wire, then plug it back in. You should see `slot 1 disconnected`, then `slot 1 connected`, with no errors added.
3. **More slaves.** Add slaves 2–4. Each one shows `connected` and passes the counter check. samples/s becomes 1000 × the number of slaves.
4. **10-minute run.** `python receiver.py <MASTER_PORT> --reset-stats --duration 600` must end with `RESULT: PASS`.

## 5. How it works

**Master** (`src/master/`)
* `sync_timer.cpp`: a hardware timer interrupt fires every 1 ms. It sends a 10 µs SYNC pulse and, after every 10th pulse, wakes the reader task.
* `spi_link.cpp`: the reader task waits 200 µs, then reads 32 bytes from each of the 4 CS slots. All four reads take about 0.5 ms. It then sends **one DATA packet** every 10 ms (even with no slaves) with every on-time slave's 10 samples, stamped with the master's pulse number, so samples from different slaves line up in time.
* `main.cpp`: sends a STATUS packet (per-slave counters) every second and handles the laptop's "reset stats" command.

**Slave** (`src/slave/main.cpp`)
* On every SYNC pulse an interrupt wakes the sample task, which takes one sample.
* Every 10 samples it builds a 32-byte frame and hands it to the SPI driver, where it waits until the master reads it.
* **Lining up with the master:** a slave starts each new batch right after the master reads the previous one. The master reads after every 10th pulse, so each batch is complete just in time for the next read. This happens automatically at power-up and after any hiccup. No setup or handshake is needed, and slaves can boot in any order.

**Checks** (portable code in `lib/`, unit-tested on the laptop)
* `crc_errors`: a frame from a connected slave arrived corrupted.
* `gaps`: 10-sample batches a connected slave failed to deliver (lost, corrupted or late).
* **Timing guarantee:** a frame is forwarded only if its sample number matches the slot's locked offset to the master's pulse count. A late (stale) frame, e.g. after a master stall, is dropped and counted as a gap instead of being sent with the wrong time.
* `overruns`: the slave had to drop a batch because the master didn't read it in time.
* An empty CS slot just reads as "not connected". It doesn't count as an error.

**Why SPI mode 1:** the ESP32's SPI slave hardware, when using DMA, has a known quirk in modes 0 and 2. ESP-IDF's docs recommend mode 1 or 3, so both sides use mode 1.

**DMA** is a built-in part of the ESP32 that moves SPI data to and from memory without the CPU. Its only rules for us: buffers come from `heap_caps_malloc(..., MALLOC_CAP_DMA)`, and frame sizes are a multiple of 4 bytes (32).

| Path | What | Portable? |
|------|------|-----------|
| `lib/protocol/` | CRC, the 32-byte SPI frame, laptop packets | yes |
| `lib/core/sample_source.*` | counter / synthetic samples. `read_sample()` is where a real ADC will plug in | yes |
| `lib/core/slave_batcher.*` | slave: batches of 10, lining up with the master's reads, overrun flag | yes |
| `lib/core/link_checker.*` | master: connected?, CRC errors, gaps, overruns per slot | yes |
| `src/master/`, `src/slave/` | ESP32-specific: timer, interrupts, SPI drivers, USB | ESP32 |
| `test/` | `pio test -e native`. `test_end_to_end` simulates 4 slaves and the master's timing | – |

Each of `lib/core`, `lib/protocol`, `src/master` and `src/slave` has its own short README with usage examples.

## 6. Data format (protocol v2)

* **SPI frame** (slave → master, 32 bytes): `A5, version=2, flags, 0, u32 first_frame, i16 samples[10], u16 0, u16 crc`. flags: bit0 overrun, bit1 counter pattern, bit2 synthetic.
* **Laptop packets:** `AA 55, version=2, type, u16 seq, u16 len, payload, u16 crc`.
  * DATA (0x01), one every 10 ms with `tick` going up by exactly 10: `u32 tick, u8 slot_mask`, then for each slot with on-time data `u8 flags, u32 first_frame, i16 samples[10]`.
  * STATUS (0x02): `u32 uptime_ms, u8 present_mask`, then for each of the 4 slots `u32 crc_errors, u32 gaps, u32 overruns, u8 last_flags`.
  * LOG (0x04): text.
  * CMD (0x10, laptop → master): `u8 cmd`, where 1 = reset stats.

## 7. Limits for now

* The master can't send anything to the slaves. Changing a slave's mode means reflashing it.
* All slots must be read within 1 ms (about 0.5 ms is used at 4 MHz). If long wires cause CRC errors, set `kSpiClockHz` to 2 MHz.
* Slaves are flashed over their own USB. Flashing them through the master could be added later using the free GPIOs.
