from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QQuaternion, QVector3D

from .rendering import RigidGeometry, load_render_assets
from .simulation import HandSimulation


class HandController(QObject):
    changed=Signal()
    bodiesChanged=Signal()
    posesChanged=Signal()
    jointNamesChanged=Signal()

    def __init__(self):
        super().__init__()
        self.simulation=HandSimulation()
        self._pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='hand-mesh-loader')
        self._asset_future=self._pool.submit(load_render_assets,Path(__file__).parent/'models/bionic_hand_delta_1_1/render_meshes.npz')
        self._bodies=[];self._poses=[];self._joints=[];self._joint_labels=[];self._targets=None
        self._asset_error=None
        self._status='Loading articulated CAD model…';self._ready=False;self._running=True
        self._sim_time=0.;self._step_hz=0;self._contacts=0;self._last_time=None
        self.simulation.start()
        self._timer=QTimer(self);self._timer.timeout.connect(self._poll);self._timer.start(16)

    def _poll(self):
        previous_ready, previous_status = self._ready, self._status
        snapshot=self.simulation.snapshot()
        if self._asset_future is not None and self._asset_future.done():
            try:
                assets=self._asset_future.result()
                self._bodies=[dict(name=name,geometry=RigidGeometry(vertices,bounds)) for name,vertices,bounds in assets]
                self.bodiesChanged.emit()
            except Exception as error:
                self._asset_error=f'CAD rendering error: {error}';self._status=self._asset_error;self.changed.emit()
            self._asset_future=None
        if not snapshot.get('ready'):
            self._ready=False
            if self._status!=snapshot['status']:
                self._status=snapshot['status'];self.changed.emit()
            return
        self._ready=bool(self._bodies)
        self._status=snapshot['status'] if self._ready else (self._asset_error or 'Loading CAD rendering assets…')
        self._sim_time=snapshot['time'];self._step_hz=snapshot['stepHz'];self._contacts=snapshot['contacts']
        body_indices={name:i for i,name in enumerate(snapshot['bodyNames'])}
        self._poses=[]
        for body in self._bodies:
            index=body_indices[body['name']]
            p=snapshot['positions'][index]*1000;q=snapshot['quaternions'][index]
            self._poses.append(dict(position=QVector3D(*map(float,p)),rotation=QQuaternion(*map(float,q))))
        if self._targets is None:self._targets=snapshot['targets'].copy()
        self._joints=[dict(name=name,label=name.replace('_',' ').title(),
                          position=float(np.degrees(snapshot['qpos'][i])),
                          target=float(np.degrees(self._targets[i])),
                          lower=float(np.degrees(snapshot['limits'][i,0])),upper=float(np.degrees(snapshot['limits'][i,1])))
                      for i,name in enumerate(snapshot['names'])]
        if not self._joint_labels:
            self._joint_labels=[joint['label'] for joint in self._joints]
            self.jointNamesChanged.emit()
        self.posesChanged.emit()
        # UI telemetry and joint text do not need to refresh at display rate.
        if self._ready != previous_ready or self._status != previous_status or self._last_time is None or abs(self._sim_time-self._last_time)>=.1 or not self._running:
            self._last_time=self._sim_time;self.changed.emit()

    def close(self):
        self._timer.stop();self.simulation.close();self._pool.shutdown(wait=True,cancel_futures=True)

    @Property(str,notify=changed)
    def status(self):return self._status
    @Property(bool,notify=changed)
    def ready(self):return self._ready
    @Property(bool,notify=changed)
    def running(self):return self._running
    @Property(float,notify=changed)
    def simTime(self):return self._sim_time
    @Property(int,notify=changed)
    def stepHz(self):return self._step_hz
    @Property(int,notify=changed)
    def contacts(self):return self._contacts
    @Property('QVariantList',notify=bodiesChanged)
    def bodies(self):return self._bodies
    @Property('QVariantList',notify=posesChanged)
    def poses(self):return self._poses
    @Property('QStringList',notify=jointNamesChanged)
    def jointLabels(self):return self._joint_labels
    @Property('QVariantList',notify=changed)
    def joints(self):return self._joints

    @Slot(bool)
    def setRunning(self,value):
        self._running=value;self.simulation.set_running(value);self.changed.emit()

    @Slot(int,float)
    def setJointTarget(self,index,degrees):
        if self._targets is None or not 0<=index<len(self._targets) or not np.isfinite(degrees):return
        joint=self._joints[index]
        self._targets[index]=np.radians(np.clip(degrees,joint['lower'],joint['upper']))
        self.simulation.set_targets(self._targets)
        self._joints[index]['target']=float(np.degrees(self._targets[index]));self.changed.emit()

    @Slot(str)
    def setPose(self,pose):
        if self._targets is None:return
        values=np.zeros_like(self._targets)
        for i,joint in enumerate(self._joints):
            name=joint['name']
            if pose=='flex' and not name.endswith('lateral'):values[i]=.35
            if pose=='spread' and name.endswith('lateral'):
                finger=name.split('_')[0];values[i]={'thumb':.15,'index':.15,'middle':0.,'ring':-.1,'little':-.15}[finger]
        self._targets=values;self.simulation.set_targets(values)
        for i,joint in enumerate(self._joints):joint['target']=float(np.degrees(values[i]))
        self.changed.emit()

    @Slot()
    def reset(self):
        if self._targets is not None:self._targets[:]=0
        self.simulation.reset();self.changed.emit()
