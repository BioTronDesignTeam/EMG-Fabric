# core

The decision logic for the master and the slaves. It's plain C++ with no hardware calls, so all of it is unit-tested on the laptop (`pio test -e native`).

| File | Runs on | What it does |
|---|---|---|
| `sample_source.*` | slave | makes one sample per SYNC pulse (counter pattern or fake EMG) |
| `slave_batcher.*` | slave | collects 10 samples into a frame, keeps batches lined up with the master's reads |
| `link_checker.*` | master | one per slot: is this frame valid and on time? Keeps the counters |

## SampleSource: where samples come from

```cpp
SampleSource src(kModeCounter);
src.read_sample(5);    // 5: the sample equals its number (12 bits), so loss is easy to spot

SampleSource emg(kModeSynthetic, seed);
emg.read_sample(n);    // noise around 2048 that swells and fades, like a muscle
```
**Plugging in a real sensor:** `read_sample()` is the only place to change. Return the ADC reading instead of made-up data.

## SlaveBatcher: 10 samples → one frame

Call this once per SYNC pulse, in this order:
```cpp
SlaveBatcher batcher(mode_flags(kModeCounter));
uint8_t frame[kSpiFrameSize];

if (master_read_last_frame) batcher.on_frame_read();
int16_t s = src.read_sample(batcher.next_sample_number());
if (batcher.add_sample(s, frame)) {
    // `frame` is complete: hand it to the SPI driver
}
```
- It starts a new batch right after the master reads, so its batches line up with the reads automatically.
- If a frame is still waiting when the next one completes, it drops the new one and counts an overrun (`batcher.overruns()`).

## LinkChecker: should the master trust this frame?

Call this once per read of a slot:
```cpp
LinkChecker checker;
SlaveFrame f;
switch (checker.on_frame(rx, tick, &f)) {
    case LinkResult::Ok:      /* valid and on time: forward f */ break;
    case LinkResult::Skip:    /* valid, timing not proven yet: drop */ break;
    case LinkResult::Invalid: /* bad CRC, or nothing connected */ break;
}
checker.present();            // is a slave connected?
checker.stats().gaps;         // batches not delivered
checker.stats().crc_errors;   // corrupted frames
```
- `tick` is the master's pulse number for `samples[0]`.
- The checker learns `tick − first_frame` and locks it once two reads in a row agree. After that it forwards only frames that match, so data is never labelled with the wrong time.
- After 1 s without a valid frame, the slot is marked absent.

## Tests
```bash
pio test -e native -f test_slave_batcher
pio test -e native -f test_link_checker
pio test -e native -f test_end_to_end     # 4 simulated slaves + master timing
```
