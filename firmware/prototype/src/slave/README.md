# slave

ESP32 firmware for a slave. It takes one sample on every SYNC pulse and, every 10 samples, has a 32-byte frame ready for the master to read.

```
SYNC pulse --> on_sync() ISR --wakes--> sample_task
                                          1. did the master read the last frame?
                                          2. take one sample
                                          3. 10 samples? queue the frame in the SPI driver
master pulls CS low --> SPI hardware sends the queued frame by itself (DMA)
```

| File | What it does |
|---|---|
| `config_slave.h` | pins, SPI mode, and the sample mode (counter or synthetic) |
| `main.cpp` | SYNC interrupt, sample task, SPI slave setup |

The logic lives in `lib/core` (`SampleSource`, `SlaveBatcher`). This folder only connects it to the ESP32 hardware.

**Every slave runs the same firmware.** Which master CS pin it's wired to decides whether it's slave 1, 2, 3 or 4.

## Build and flash
```bash
pio run -e slave -t upload --upload-port /dev/cu.usbserial-XXXX   # repeat for each slave
pio device monitor -e slave --port /dev/cu.usbserial-XXXX         # optional debug line
# sync_edges=53000 samples=53000 overruns=0 realigned=1
```
`sync_edges` should grow by 1000 per second. If it stays at 0, check the SYNC wire.

## Examples

**Switch to synthetic EMG** (in `platformio.ini`, under `[env:slave]`), then reflash:
```ini
build_flags = ${esp32.build_flags} -DSLAVE_MODE=2
```

**Plug in a real sensor:** only `SampleSource::read_sample()` in `lib/core/sample_source.cpp` changes.
```cpp
int16_t SampleSource::read_sample(uint32_t n) {
    return my_adc_read();   // must be fast: it runs once per SYNC pulse
}
```
After that, re-check that the frame is still queued well within 200 µs of the pulse.

## Rules
- **Keep `on_sync()` tiny.** It's an interrupt: no printing, no waiting, just wake the task.
- **The frame buffer must be DMA memory** (`heap_caps_malloc(..., MALLOC_CAP_DMA)`), because the SPI hardware reads it directly.
- **Never print to the SPI path.** Debug text goes to the slave's own USB port only.
