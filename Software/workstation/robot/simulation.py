"""MuJoCo owns its model/data on an independent fixed-step physics worker."""
import threading
import time
from pathlib import Path

import numpy as np


class HandSimulation:
    def __init__(self, model_path=None):
        self.model_path = Path(model_path or Path(__file__).parent/'models/bionic_hand_delta_1_1/hand_simulation.xml')
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name='mujoco-physics', daemon=True)
        self._running = True
        self._targets = None
        self._reset = False
        self._snapshot = dict(status='Loading MuJoCo model…', ready=False)

    def start(self): self._thread.start()

    def close(self):
        self._stop.set()
        self._thread.join(timeout=5)

    def snapshot(self):
        with self._lock:
            return self._snapshot.copy()

    def set_running(self, value):
        with self._lock: self._running = bool(value)

    def set_targets(self, values):
        with self._lock: self._targets = np.array(values, dtype=float)

    def reset(self):
        with self._lock: self._reset = True

    def _run(self):
        try:
            import mujoco
            model = mujoco.MjModel.from_xml_path(str(self.model_path))
            data = mujoco.MjData(model)
            mujoco.mj_forward(model,data)
            limits = model.actuator_ctrlrange.copy()
            names = [mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_JOINT,i) for i in range(model.njnt)]
            targets = np.zeros(model.nu)
            deadline = time.monotonic()
            last_publish = 0.
            while not self._stop.is_set():
                with self._lock:
                    running, reset = self._running,self._reset
                    self._reset = False
                    incoming = self._targets
                if incoming is not None and incoming.shape == targets.shape and np.isfinite(incoming).all():
                    targets = np.clip(incoming,limits[:,0],limits[:,1])
                if reset:
                    mujoco.mj_resetData(model,data)
                    targets[:] = 0
                    with self._lock: self._targets = targets.copy()
                    mujoco.mj_forward(model,data)
                data.ctrl[:] = targets
                if running: mujoco.mj_step(model,data)
                now = time.monotonic()
                if now-last_publish >= 1/60:
                    snapshot = dict(status='MuJoCo running' if running else 'MuJoCo paused',ready=True,
                                    time=float(data.time),qpos=data.qpos.copy(),targets=targets.copy(),
                                    positions=data.xpos.copy(),quaternions=data.xquat.copy(),
                                    names=names,bodyNames=[mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_BODY,i) for i in range(model.nbody)],limits=limits,stepHz=round(1/model.opt.timestep),
                                    contacts=int(data.ncon))
                    with self._lock: self._snapshot = snapshot
                    last_publish = now
                deadline += model.opt.timestep
                self._stop.wait(max(0,deadline-time.monotonic()))
                # Drop wall-clock backlog instead of monopolizing CPU after a stall.
                if time.monotonic()-deadline > .1: deadline = time.monotonic()
        except Exception as error:
            with self._lock: self._snapshot = dict(status=f'MuJoCo error: {error}',ready=False)
