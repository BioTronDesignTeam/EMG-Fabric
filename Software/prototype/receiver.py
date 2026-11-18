"""Receive and check the EMG prototype's data stream from the master.

    python receiver.py <port>                   # live dashboard
    python receiver.py <port> --reset-stats     # clear the master's counters first
    python receiver.py <port> --duration 600    # 10-minute test run, ends with RESULT: PASS/FAIL
    python receiver.py <port> --plot            # live plot of every slave (needs matplotlib)

Find the port with:  python -m serial.tools.list_ports
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections import deque

import emg_protocol as p

try:
    import serial  # pyserial
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:  # pragma: no cover
    sys.exit("missing packages: pip install -r requirements.txt")


class Stats:
    def __init__(self) -> None:
        self.packets = 0
        self.samples = 0
        self.lost_packets = 0      # packets lost between master and laptop (seq gaps)
        self.seq_jumps = 0         # sequence restarted or jumped: master reset or stale data
        self.missed_ticks = 0      # 10 ms DATA windows that never arrived
        self.last_tick: int | None = None
        self.counter_checked = [0] * p.MAX_SLOTS  # frames checked against the counter test pattern
        self.counter_bad = [0] * p.MAX_SLOTS
        self.status: p.Status | None = None
        self.last_seq: int | None = None
        self.win_packets = 0
        self.win_samples = 0
        self.packet_rate = 0.0
        self.sample_rate = 0.0
        self.log: deque[Text] = deque(maxlen=12)

    def on_seq(self, seq: int) -> None:
        if self.last_seq is not None:
            gap = (seq - self.last_seq - 1) & 0xFFFF
            if gap < 1000:
                self.lost_packets += gap
            else:
                self.seq_jumps += 1
        self.last_seq = seq

    def on_tick(self, tick: int) -> None:
        if self.last_tick is not None:
            step = (tick - self.last_tick) & 0xFFFFFFFF
            if step % 10 == 0 and 0 < step < 1_000_000:
                self.missed_ticks += step // 10 - 1
            else:
                self.missed_ticks += 1  # master restarted
        self.last_tick = tick

    def update_rates(self, dt: float) -> None:
        self.packet_rate = self.win_packets / dt
        self.sample_rate = self.win_samples / dt
        self.win_packets = self.win_samples = 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port")
    ap.add_argument("--baud", type=int, default=921600)
    ap.add_argument("--reset-stats", action="store_true", help="clear the master's counters at start")
    ap.add_argument("--duration", type=float, default=0, help="stop after N seconds and print PASS/FAIL")
    ap.add_argument("--plot", action="store_true", help="live plot (matplotlib)")
    args = ap.parse_args()

    plot = LivePlot() if args.plot else None  # before opening: matplotlib can take seconds to load

    # Opening a port toggles DTR/RTS, which resets most ESP32 dev boards.
    # Keeping both low helps on some, but ours still reset; that's accepted.
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = args.port, args.baud, 0.005
    ser.dtr = ser.rts = False
    ser.open()
    ser.reset_input_buffer()
    if args.reset_stats:
        ser.write(p.encode_packet(p.PKT_CMD, 0, p.encode_cmd(p.CMD_RESET_STATS)))

    console = Console()
    parser = p.PacketParser()
    st = Stats()
    start = last_rate = last_draw = time.monotonic()
    try:
        with Live(render(st, parser, args, 0), console=console, auto_refresh=False) as live:
            while not args.duration or time.monotonic() - start < args.duration:
                for pkt in parser.feed(ser.read(ser.in_waiting or 1)):  # whatever has arrived; never wait long
                    handle(pkt, st, plot)

                now = time.monotonic()
                if now - last_rate >= 1.0:
                    st.update_rates(now - last_rate)
                    last_rate = now
                if now - last_draw >= 0.25:
                    live.update(render(st, parser, args, now - start), refresh=True)
                    last_draw = now
                if plot:
                    plot.refresh()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
    return print_summary(console, st, parser, time.monotonic() - start)


def handle(pkt: p.Packet, st: Stats, plot: LivePlot | None) -> None:
    st.packets += 1
    st.win_packets += 1
    st.on_seq(pkt.seq)
    try:
        if pkt.type == p.PKT_DATA:
            d = p.decode_data(pkt.payload)
            st.on_tick(d.tick)
            if plot:
                plot.add(d)
            for slot, e in d.slots.items():
                st.samples += len(e.samples)
                st.win_samples += len(e.samples)
                if e.flags & p.FLAG_COUNTER:
                    st.counter_checked[slot] += 1
                    st.counter_bad[slot] += p.counter_errors(e) > 0
        elif pkt.type == p.PKT_STATUS:
            st.status = p.decode_status(pkt.payload)
        elif pkt.type == p.PKT_LOG:
            st.log.append(Text(pkt.payload.decode("utf-8", "replace")))
    except ValueError as err:
        st.log.append(Text(f"bad packet payload (type 0x{pkt.type:02x}): {err}", style="red"))


# ---- Dashboard ---------------------------------------------------------------


def count(v: int, bad: str = "red") -> Text:
    return Text(str(v), style=bad if v else "green")


def render(st: Stats, parser: p.PacketParser, args: argparse.Namespace, elapsed: float) -> Panel:
    link = Table.grid(padding=(0, 3))
    link.add_row(
        Text(f"{st.packet_rate:.0f} pkt/s", style="bold"),
        Text(f"{st.sample_rate:,.0f} samples/s", style="bold"),
        Text.assemble("usb crc ", count(parser.crc_errors)),
        Text.assemble("lost ", count(st.lost_packets)),
        Text.assemble("seq jumps ", count(st.seq_jumps, "yellow")),
        Text.assemble("missed ticks ", count(st.missed_ticks)),
    )

    slaves = Table(expand=True, header_style="bold cyan")
    for col in ("slot", "state", "mode", "crc errors", "gaps", "overruns", "counter check"):
        slaves.add_column(col, justify="left" if col in ("slot", "state", "mode") else "right")
    for i in range(p.MAX_SLOTS):
        s = st.status
        present = bool(s and s.present_mask & (1 << i))
        checked, bad = st.counter_checked[i], st.counter_bad[i]
        check = Text("—", style="dim")
        if checked:
            check = Text(f"{'PASS' if not bad else 'FAIL'} {checked - bad:,}/{checked:,}", style="green" if not bad else "bold red")
        if not present:
            slaves.add_row(f"{i + 1}", Text("○ absent", style="dim"), "", "", "", "", check)
            continue
        e = s.slots[i]
        slaves.add_row(
            f"{i + 1}",
            Text("● present", style="green"),
            p.flags_str(e.last_flags),
            count(e.crc_errors),
            count(e.gaps, "yellow"),
            count(e.overruns, "yellow"),
            check,
        )

    parts: list = [link, slaves]
    if st.log:
        parts.append(Panel(Group(*st.log), title="master log", title_align="left", border_style="dim"))

    title = f"EMG receiver · {args.port}"
    if st.status:
        title += f" · master up {st.status.uptime_ms // 1000}s"
    subtitle = f"{elapsed:.0f}s" + (f" / {args.duration:.0f}s" if args.duration else "") + " · ctrl-c to stop"
    return Panel(Group(*parts), title=title, title_align="left", subtitle=subtitle, subtitle_align="right", border_style="blue")


def print_summary(console: Console, st: Stats, parser: p.PacketParser, elapsed: float) -> int:
    problems = []
    if parser.crc_errors:
        problems.append(f"USB CRC errors: {parser.crc_errors}")
    if st.lost_packets:
        problems.append(f"USB packets lost: {st.lost_packets}")
    if st.missed_ticks:
        problems.append(f"DATA windows missing: {st.missed_ticks} x 10 ms")
    if st.seq_jumps:
        problems.append(f"packet sequence jumped {st.seq_jumps}x (master restarted?)")
    for i in range(p.MAX_SLOTS):
        if st.counter_bad[i]:
            problems.append(f"slave{i + 1} counter check failed in {st.counter_bad[i]}/{st.counter_checked[i]} frames")
    if st.samples == 0:
        problems.append("no samples received")
    if st.status:
        for i, e in enumerate(st.status.slots):
            for name in ("crc_errors", "gaps", "overruns"):
                if getattr(e, name):
                    problems.append(f"slave{i + 1} {name}: {getattr(e, name)}")
    console.print(f"\n[bold]=== {elapsed:.0f} s: {st.packets:,} packets, {st.samples:,} samples ===[/]")
    for msg in problems:
        console.print(f"  [red]FAIL:[/] {msg}")
    console.print("RESULT:", "[bold red]FAIL[/]" if problems else "[bold green]PASS[/]")
    return 1 if problems else 0


class LivePlot:
    """The last 5 seconds on the master's time axis (tick), one line per slot.
    Missing data is drawn as a blank space, so gaps and dropouts are visible."""

    WINDOW = 5000  # ticks = 5 s
    FPS = 25

    def __init__(self) -> None:
        import matplotlib.pyplot as plt  # only needed with --plot
        import numpy as np

        self.plt, self.np = plt, np
        self.ticks: deque[int] = deque(maxlen=self.WINDOW)
        self.data = [deque(maxlen=self.WINDOW) for _ in range(p.MAX_SLOTS)]
        plt.ion()
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.lines = [self.ax.plot([], [], lw=0.8, label=f"slave {s + 1}")[0] for s in range(p.MAX_SLOTS)]
        self.ax.set_ylim(0, 4096)  # fixed: no rescaling jitter (samples are 12-bit)
        self.ax.set_xlabel("master tick (ms)")
        self.ax.set_title("EMG prototype")
        self.ax.legend(loc="upper right")
        plt.show(block=False)
        self.last = 0.0

    def add(self, d: p.Data) -> None:
        if self.ticks and d.tick < self.ticks[-1]:  # master restarted: start over
            self.ticks.clear()
            for ys in self.data:
                ys.clear()
        for i in range(p.SAMPLES_PER_FRAME):
            self.ticks.append(d.tick + i)
            for s in range(p.MAX_SLOTS):
                e = d.slots.get(s)
                self.data[s].append(e.samples[i] if e else math.nan)

    def refresh(self) -> None:
        now = time.monotonic()
        if now - self.last < 1 / self.FPS or not self.ticks or not self.plt.fignum_exists(self.fig.number):
            return
        self.last = now
        np = self.np
        x = np.fromiter(self.ticks, float, len(self.ticks))
        for line, ys in zip(self.lines, self.data):
            line.set_data(x, np.fromiter(ys, float, len(ys)))
        self.ax.set_xlim(self.ticks[-1] - self.WINDOW, self.ticks[-1])
        self.fig.canvas.draw_idle()
        self.fig.canvas.flush_events()


if __name__ == "__main__":
    sys.exit(main())
