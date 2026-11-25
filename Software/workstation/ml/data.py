import threading
import time
import h5py
import pandas as pd
import numpy as np

from workstation.core.messages import SignalBlock


class EMGData:

    def __init__(self,path):
        self.path = path
        self.filename = path.stem
        if path.suffix == ".hdf5":
            with h5py.File(path, 'r') as f:
                self.data = f['emg2pose']['timeseries']
                self.time = np.array(self.data['time'])
                self.emg = np.array(self.data['emg'])/1000
                self.joint_angles = np.array(self.data['joint_angles'])
        elif path.suffix == ".csv":
            df = pd.read_csv(path)
            

    def info(self):
        print(f"{'emg shape: ':<20}{self.emg.shape}")
        print(f"{'joint_angles shape: ':<20} {self.joint_angles.shape}")
        print(f"{'time shape: ':<20} {self.time.shape}")
        print(f"{'missing data: ':<20} {np.isnan(self.joint_angles).sum()}")


class FileSource:
    def __init__(self, bus, recording):
        self.bus = bus
        self.recording = recording

        self.sample_rate = 2000  # Replace with actual recording rate if different

        self._stop = threading.Event()
        self._running = threading.Event()
        self._running.set()

        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def set_running(self, running):
        self._running.set() if running else self._running.clear()

    def close(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self):
        index = 0
        block_size = int(self.sample_rate * 0.02)  # 20 ms

        total_samples = self.recording.emg.shape[0]

        deadline = time.monotonic()

        while not self._stop.is_set():

            if self._running.is_set():

                # Restart playback when reaching the end.
                if index >= total_samples:
                    index = 0

                end = min(index + block_size, total_samples)

                #(T x C) -> (C x T)
                samples = self.recording.emg[index:end].T.copy()
                labels = self.recording.joint_angles[index:end].T.copy()
                samples.setflags(write=False)
                labels.setflags(write=False)

                self.bus.publish(
                    SignalBlock(index, self.sample_rate, samples, labels)
                )

                index = end

            deadline += 0.02

            self._stop.wait(max(0, deadline - time.monotonic()))

            if time.monotonic() - deadline > 0.1:
                deadline = time.monotonic()
