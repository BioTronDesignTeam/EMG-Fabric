import threading
import time

import numpy as np

from ..core.messages import SignalBlock


class SyntheticSource:
    """Independent acquisition clock; generates 20 ms blocks at 2 kSPS."""

    sample_rate = 2000

    def __init__(self, bus):
        self.bus = bus
        self._stop = threading.Event()
        self._running = threading.Event()
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._lock = threading.Lock()
        self._lead_field = np.zeros((4, 4))
        self._activation = np.array([1., .35, .2, .15])

    def configure_phantom(self, lead_field, activation):
        with self._lock:
            self._lead_field = np.array(lead_field, copy=True)
            self._activation = np.array(activation, copy=True)

    def start(self):
        self._thread.start()

    def set_running(self, running):
        self._running.set() if running else self._running.clear()

    def close(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self):
        rng = np.random.default_rng(42)
        index = 0
        deadline = time.monotonic()
        while not self._stop.is_set():
            if self._running.is_set():
                t = (index + np.arange(40)) / self.sample_rate
                envelope = 0.15 + 0.65 * np.maximum(0, np.sin(t * 2.0))
                muscle = np.array([
                    envelope * (0.32 * rng.standard_normal(40)
                    + 0.15 * np.sin(2 * np.pi * (83 + c * 27) * t))
                    for c in range(4)
                ])
                with self._lock:
                    lead_field = self._lead_field.copy()
                    activation = self._activation.copy()
                # Linear superposition of independent source currents through
                # the solved volume conductor; output is millivolts.
                samples = lead_field @ (activation[:, None] * muscle)
                samples.setflags(write=False)
                labels = None
                self.bus.publish(SignalBlock(index, self.sample_rate, samples, labels))
                index += 40
            deadline += 0.02
            self._stop.wait(max(0, deadline - time.monotonic()))
            if time.monotonic() - deadline > 0.1:
                deadline = time.monotonic()
