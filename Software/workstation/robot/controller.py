from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
from PySide6.QtGui import QQuaternion, QVector3D

from .rendering import RigidGeometry, load_mujoco_render_assets, load_render_assets
from .simulation import HandSimulation
from queue import Empty

_MODELS = {
    'bionic': {
        'name': 'Bionic Hand',
        'simulation': 'bionic_hand_delta_1_1/hand_simulation.xml',
        'assets': 'bionic_hand_delta_1_1/render_meshes.npz',
        'loader': load_render_assets,
    },
    'shadow': {
        'name': 'Shadow Hand',
        'simulation': 'shadow_hand_right/right_hand.xml',
        'assets': 'shadow_hand_right/right_hand.xml',
        'loader': load_mujoco_render_assets,
    },
}

joint_to_label = [
    -1,  # 0
    -1,  # 1
    4,   # 2
    5,   # 3
    6,   # 4
    7,   # 5
    8,   # 6
    9,   # 7
    10,  # 8
    11,  # 9
    12,  # 10
    13,  # 11
    14,  # 12
    15,  # 13
    -1,  # 14
    16,  # 15
    17,  # 16
    18,  # 17
    19,  # 18
    1,   # 19
    0,   # 20
    -1,  # 21
    2,   # 22
    3,   # 23
]

class HandController(QObject):
    bus = None
    changed=Signal()
    plotchanged=Signal()
    bodiesChanged=Signal()
    posesChanged=Signal()
    jointNamesChanged=Signal()

    def __init__(self):
        super().__init__()
        self._queue = self.bus.subscribe()
        self._model_id='bionic'
        self._channel_count=20
        model=_MODELS[self._model_id]
        self.simulation=HandSimulation(Path(__file__).parent/'models'/model['simulation'])
        self._pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='hand-mesh-loader')
        self._asset_future=self._pool.submit(model['loader'],Path(__file__).parent/'models'/model['assets'])
        self._bodies=[];self._poses=[];self._joints=[];self._joint_labels=[];self._targets=None
        self._asset_error=None
        self._status='Loading articulated CAD model…';self._ready=False;self._running=True
        self._plot_label = False
        self._sim_time=0.;self._step_hz=0;self._contacts=0;self._last_time=None
        self.simulation.start()
        self._timer=QTimer(self);self._timer.timeout.connect(self._poll);self._timer.timeout.connect(self.consume);self._timer.start(16)

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
        self._joints=[dict(name=name,label=(name.replace('_',' ').replace(' servo','').title()
                                                 if self._model_id=='bionic' else name.removeprefix('rh_')),
                          position=float(np.degrees(snapshot['channelPositions'][i])),
                          target=float(np.degrees(self._targets[i])),
                          lower=float(np.degrees(snapshot['limits'][i,0])),upper=float(np.degrees(snapshot['limits'][i,1])),
                          unit='°')
                      for i,name in enumerate(snapshot['names'])]
        labels=[joint['label'] for joint in self._joints]
        if labels!=self._joint_labels:
            self._joint_labels=labels
            self.jointNamesChanged.emit()
        self.posesChanged.emit()
        # UI telemetry and joint text do not need to refresh at display rate.
        if self._ready != previous_ready or self._status != previous_status or self._last_time is None or abs(self._sim_time-self._last_time)>=.1 or not self._running:
            self._last_time=self._sim_time;self.changed.emit()

    def consume(self):
        latest_block = None

        while True:
            try:
                latest_block = self._queue.get_nowait()
            except Empty:
                break
        if latest_block is None or latest_block.labels is None:
            return
        angles = latest_block.labels[:, -1]
        for joint_index, label_index in enumerate(joint_to_label):
            if label_index != -1:
                self.actuator_targets = angles[joint_to_label]
        if self._plot_label:
            self.update_label()


    def close(self):
        self._timer.stop();self.simulation.close();self._pool.shutdown(wait=True,cancel_futures=True)

    def update_label(self):
        for i in range(len(self.actuator_targets)):
            self.setJointTarget(i,self.actuator_targets[i]*150/3.14)


    @Slot(str)
    def setModel(self,model_id):
        if model_id not in _MODELS:
            self._status=f'Unknown hand model: {model_id}'
            self.changed.emit()
            return
        if model_id==self._model_id:return
        self.simulation.close()
        self._model_id=model_id
        model=_MODELS[model_id]
        self.simulation=HandSimulation(Path(__file__).parent/'models'/model['simulation'])
        self.simulation.set_running(self._running)
        self.simulation.start()
        self._asset_future=self._pool.submit(model['loader'],Path(__file__).parent/'models'/model['assets'])
        self._bodies=[];self._poses=[];self._joints=[];self._joint_labels=[];self._targets=None
        self._asset_error=None;self._status=f'Loading {model["name"]}…';self._ready=False
        self._sim_time=0.;self._step_hz=0;self._contacts=0;self._last_time=None
        self.bodiesChanged.emit();self.posesChanged.emit();self.jointNamesChanged.emit();self.changed.emit()

    @Property(str,notify=changed)
    def status(self):return self._status
    @Property(bool,notify=changed)
    def ready(self):return self._ready
    @Property(bool,notify=changed)
    def running(self):return self._running
    @Property(str,notify=changed)
    def modelName(self):return _MODELS[self._model_id]['name']
    @Property(int,notify=changed)
    def modelIndex(self):return list(_MODELS).index(self._model_id)
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

    @Property(bool, notify=plotchanged)
    def plot_label(self):
        return self._plot_label

    @Slot()
    def toggleplot(self):
        self._plot_label = not self._plot_label
        self.plotchanged.emit()
    
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
            if self._model_id=='bionic':
                if pose=='flex' and not name.endswith('lateral'):values[i]=.35
                if pose=='spread' and name.endswith('lateral'):
                    finger=name.split('_')[0];values[i]={'thumb':.15,'index':.15,'middle':0.,'ring':-.1,'little':-.15}[finger]
            elif pose=='flex' and not name.startswith('rh_WRJ') and name.endswith(('J3','J2','J1','J0')):
                values[i]=np.radians(joint['lower']+.65*(joint['upper']-joint['lower']))
            elif pose=='spread':
                spread={'rh_FFJ4':.15,'rh_MFJ4':0.,'rh_RFJ4':-.1,'rh_LFJ4':-.15,'rh_LFJ5':.15,'rh_THJ5':.15}
                if name in spread:values[i]=spread[name]
        self._targets=values;self.simulation.set_targets(values)
        for i,joint in enumerate(self._joints):joint['target']=float(np.degrees(values[i]))
        self.changed.emit()

    @Slot()
    def reset(self):
        if self._targets is not None:
            for i,joint in enumerate(self._joints):
                self._targets[i]=np.radians(np.clip(0,joint['lower'],joint['upper']))
        self.simulation.reset();self.changed.emit()
