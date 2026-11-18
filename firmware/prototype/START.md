# EMG Fabric Armband Firmware

Welcome to the firmware team of EMG Fabric. This directory contains all code that runs on the MCUs on the EMG armband.

## 0. Getting started
We use PlatformIO in VS Code. Setup guides:
- https://docs.platformio.org/en/latest/tutorials/espressif32/espidf_debugging_unit_testing_analysis.html
- https://www.youtube.com/watch?v=JmvMvIphMnY

Open the `firmware/prototype` folder itself in VS Code, not the repo root.

## 1. Learning the code base
Read these in order:
1. The prototype design doc (shared with the team): what the system does and why.
2. [`README.md`](README.md): wiring, build and flash, testing checklist.
3. The folder READMEs, each with short examples:
   - [`lib/protocol`](lib/protocol/README.md): byte formats (SPI frames, laptop packets, CRC)
   - [`lib/core`](lib/core/README.md): batching and link-checking logic
   - [`src/master`](src/master/README.md): master firmware
   - [`src/slave`](src/slave/README.md): slave firmware
4. [`../../Software/prototype/README.md`](../../Software/prototype/README.md): the laptop receiver.

## 2. Your first run
```bash
pio test -e native     # unit tests, no hardware needed
pio run                # build master and slave
```
Then follow the testing checklist in `README.md`.
