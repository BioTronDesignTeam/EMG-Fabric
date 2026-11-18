from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from .rendering import FieldGeometry, LayerGeometry
from .anatomy import DEFAULT_ANATOMY
from .solver import PhantomSolver
from .section import SectionGeometry, SectionOutlines, prepare_section
from .sources import source_markers


class PhantomController(QObject):
    changed = Signal()
    placementChanged = Signal()
    activationChanged = Signal()
    metricsChanged = Signal()
    sourceChanged = Signal()
    channelCountChanged = Signal()
    sectionChanged = Signal()

    def __init__(self, source):
        super().__init__()
        self.source = source
        self.solver = None
        self._geometry = FieldGeometry()
        a = DEFAULT_ANATOMY
        self._section = SectionGeometry()
        self._section_outlines = SectionOutlines(a)
        self._section_visible = False
        self._section_axial = 15.
        self._section_metrics = {}
        self._section_future = None
        self._section_key = None
        self._section_timer = QTimer(self)
        self._section_timer.setInterval(33)
        self._section_timer.timeout.connect(self._poll_section)
        self._bone = LayerGeometry(0, a.bone_radius, a.length, False)
        self._muscle = LayerGeometry(a.bone_radius, a.muscle_radius, a.length, True)
        self._skin = LayerGeometry(a.muscle_radius, a.radius, a.length, True)
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(33)
        self._update_timer.timeout.connect(self._update)
        self._angle, self._axial, self._spacing = 0., 0., 20.
        self._selected_source = 0
        self._channel_count = 4
        self._activation = [1., .35, .2, .15]
        self._status = 'Meshing and solving…'
        self._metrics = {}
        self._scale = 0.
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='phantom-fea')
        self._future = self._pool.submit(PhantomSolver)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._timer.start(50)

    def _poll(self):
        if not self._future.done():
            return
        self._timer.stop()
        try:
            self.solver = self._future.result()
            self._status = 'Solved · 3D linear tetrahedral FEM'
            self._scale = self._geometry.update_field(self.solver, self._selected_source)
            self._update()
            self.changed.emit()
        except Exception as error:
            self._status = f'FEA failed: {error}'
            self.changed.emit()

    def close(self):
        self._timer.stop()
        self._update_timer.stop()
        self._section_timer.stop()
        self._pool.shutdown(wait=True, cancel_futures=True)

    def _update(self):
        if self.solver is not None:
            lead = self.solver.lead_field(self._angle, self._axial, self._spacing, self._channel_count)
            self.source.configure_phantom(lead, self._activation)
            # Equal uncorrelated unit-RMS sources; fraction of CH1 power from
            # non-target sources, deliberately independent of activation sliders.
            power = lead[0] ** 2
            cross = float((power.sum() - power[self._selected_source]) / power.sum() * 100) if power.sum() > 1e-24 else None
            self._metrics = dict(nodes=len(self.solver.mesh.nodes),
                                 elements=len(self.solver.mesh.elements),
                                 solveMs=round(self.solver.elapsed_ms, 1),
                                 residual=f'{self.solver.residual:.2e}',
                                 sensitivity=f'{lead[0, self._selected_source]:.5f}',
                                 crossTalk='undefined' if cross is None else f'{cross:.1f} %',
                                 fieldMax=f'{self._scale:.4f}',
                                 leadField='\n'.join('CH%d: ' % (i+1) + '  '.join(f'{x:.4f}' for x in row) for i, row in enumerate(lead)))
        self.metricsChanged.emit()

    def _schedule_update(self):
        if not self._update_timer.isActive():
            self._update_timer.start()

    @Property(QObject, constant=True)
    def geometry(self): return self._geometry

    @Property(QObject, constant=True)
    def boneGeometry(self): return self._bone

    @Property(QObject, constant=True)
    def muscleGeometry(self): return self._muscle

    @Property(QObject, constant=True)
    def skinGeometry(self): return self._skin

    @Property('QVariantMap', constant=True)
    def anatomy(self):
        a = DEFAULT_ANATOMY
        return dict(boneRadius=a.bone_radius*1000, muscleRadius=a.muscle_radius*1000,
                    muscleThickness=a.muscle_thickness*1000, skinThickness=a.skin_thickness*1000,
                    radius=a.radius*1000, length=a.length*1000, sourceRadius=a.source_radius*1000)

    @Property('QVariantList', constant=True)
    def sourceMarkers(self): return source_markers()

    @Property(str, notify=changed)
    def status(self): return self._status

    @Property(bool, notify=changed)
    def ready(self): return self.solver is not None

    @Property('QVariantMap', notify=metricsChanged)
    def metrics(self): return self._metrics

    @Property(float, notify=placementChanged)
    def angle(self): return self._angle

    @Property(float, notify=placementChanged)
    def axial(self): return self._axial

    @Property(float, notify=placementChanged)
    def spacing(self): return self._spacing

    @Property(int, notify=sourceChanged)
    def selectedSource(self): return self._selected_source

    @Property('QVariantList', notify=activationChanged)
    def activations(self): return self._activation

    @Property(QObject, constant=True)
    def sectionGeometry(self): return self._section

    @Property(QObject, constant=True)
    def sectionOutlines(self): return self._section_outlines

    @Property(bool, notify=sectionChanged)
    def sectionVisible(self): return self._section_visible

    @Property(float, notify=sectionChanged)
    def sectionAxial(self): return self._section_axial

    @Property('QVariantMap', notify=sectionChanged)
    def sectionMetrics(self): return self._section_metrics

    @Slot(bool)
    def showSection(self, visible):
        self._section_visible = visible
        if visible:
            self._section_timer.start()
        else:
            self._section_timer.stop()
        self.sectionChanged.emit()

    @Slot(float)
    def setSectionAxial(self, value):
        if np.isfinite(value):
            self._section_axial = float(np.clip(value, -120, 120))
            self.sectionChanged.emit()

    def _poll_section(self):
        if self.solver is None:
            return
        desired = (self._section_axial, self._selected_source)
        if self._section_future is not None:
            if not self._section_future.done():
                return
            try:
                result = self._section_future.result()
                if desired == self._section_key:
                    self._section_metrics = self._section.apply_section(result)
                    self._section_metrics['axial'] = self._section_key[0]
                    self._section_metrics['source'] = self._section_key[1]
                    self.sectionChanged.emit()
            except Exception as error:
                self._section_metrics = dict(error=str(error))
                self.sectionChanged.emit()
            self._section_future = None
        if desired != (self._section_metrics.get('axial'), self._section_metrics.get('source')):
            self._section_key = desired
            self._section_future = self._pool.submit(prepare_section, self.solver, *desired)

    @Property(int, notify=channelCountChanged)
    def channelCount(self): return self._channel_count

    @Slot(int)
    def setChannelCount(self, count):
        if count not in (2, 4, 8, 16) or count == self._channel_count:
            return
        self._channel_count = count
        self.channelCountChanged.emit()
        # Reconfigure even while acquisition is paused. No remeshing/solve is
        # needed: all channels sample the same cached four-source FEM basis.
        self._update()

    @Slot(float, float, float)
    def place(self, angle, axial, spacing):
        if not all(np.isfinite([angle, axial, spacing])):
            return
        self._angle = angle % 360
        self._spacing = float(np.clip(spacing, 5, 50))
        bound = 120 - self._spacing / 2
        self._axial = float(np.clip(axial, -bound, bound))
        self.placementChanged.emit()
        self._schedule_update()

    @Slot(int)
    def selectSource(self, index):
        self._selected_source = max(0, min(3, index))
        if self.solver:
            self._scale = self._geometry.update_field(self.solver, self._selected_source)
        self.sourceChanged.emit()
        self._schedule_update()

    @Slot(int, float)
    def activate(self, index, value):
        if 0 <= index < 4 and np.isfinite(value):
            self._activation[index] = float(np.clip(value, 0, 1))
            self.activationChanged.emit()
            self._schedule_update()
