# EMG prototype: laptop receiver

Reads the master ESP32's data stream over USB and checks it. Wiring and firmware: [`firmware/prototype/README.md`](../../firmware/prototype/README.md).

```bash
cd EMG-Fabric/Software/prototype
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m serial.tools.list_ports                      # find the master's port

python receiver.py <port>                               # live dashboard (stats per slave)
python receiver.py <port> --reset-stats                 # clear the master's counters first
python receiver.py <port> --reset-stats --duration 600  # 10-minute run: RESULT: PASS/FAIL (exit code 0/1)
python receiver.py <port> --plot                        # live plot, one line per slave
```

The dashboard shows:
* packets/s and samples/s (1000 samples/s per connected slave);
* USB link errors (`usb crc`, `lost`, `seq jumps`) and `missed ticks`: 10 ms DATA windows that never arrived;
* one row per slot: present or absent, mode, and the master's counters (`crc errors`, `gaps`, `overruns`);
* `counter check` (per slot): every sample of the counter test pattern must equal `(first_frame + i) & 0x0FFF`.

| File | Purpose |
|------|---------|
| `emg_protocol.py` | packet encode/decode (mirror of `firmware/prototype/lib/protocol/host_packet.cpp`) |
| `receiver.py` | the command-line tool above |
| `test_protocol.py` | `python -m unittest -v test_protocol` (no hardware needed) |
| `gen_golden.py` | regenerates `firmware/prototype/test/golden/host_packets_v2.txt`, shared by the C and Python tests. Only rerun it after an intentional protocol change. |
