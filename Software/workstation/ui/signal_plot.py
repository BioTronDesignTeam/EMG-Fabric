from queue import Empty

import numpy as np
from PySide6.QtCore import QPointF, Property, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from PySide6.QtQuick import QQuickPaintedItem

DATA_TYPES = ["emg","joint_angle"]

class SignalPlot(QQuickPaintedItem):
    """Vectorized peak decimation on the GUI thread; cheap render-thread blit.

    The render callback must never run thousands of Python/NumPy reductions:
    Python paint callbacks contend with GUI slots for the GIL in Qt's renderer.
    """
    bus = None
    channelCountChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = np.zeros((4, 4000))
        self._channel_count = 4
        self._data_type = "emg"
        self._write = 0
        self._image = QImage()
        self._dirty = True
        self._queue = self.bus.subscribe()
        self.widthChanged.connect(self._invalidate)
        self.heightChanged.connect(self._invalidate)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.consume)
        self.timer.start(33)

    def _invalidate(self):
        self._dirty = True

    @Property(str, constant=True)
    def data_type(self):
        return self._data_type
    
    @data_type.setter
    def data_type(self, data_type): 
        self._data_type = data_type
        if self._data_type == "joint_angles":
            self.channelCount = 20

        
    @Property(int, notify=channelCountChanged)
    def channelCount(self):
        return self._channel_count

    @channelCount.setter
    def channelCount(self, count):
        #if count not in (2, 4, 8, 16) or count == self._channel_count:
        #    return
        self._channel_count = count
        self.data = np.zeros((count, 4000))
        self._write = 0
        self._dirty = True
        self.channelCountChanged.emit()

    def consume(self):
        changed = False
        while True:
            try:
                block = self._queue.get_nowait()
            except Empty:
                break
            if self._data_type == "joint_angles":
                if block.labels is None:
                    continue
                samples = block.labels[:, -4000:]
            else:
                samples = block.samples[:, -4000:]
            # Discard queued blocks from the previous channel layout.
            if samples.shape[0] != self._channel_count:
                continue
            n = samples.shape[1]
            first = min(n, 4000-self._write)
            self.data[:, self._write:self._write+first] = samples[:, :first]
            if first < n:
                self.data[:, :n-first] = samples[:, first:]
            self._write = (self._write+n) % 4000
            changed = True
        if (changed or self._dirty) and self.isVisible():
            self.prepare_image()
            self.update()
            self._dirty = False

    def prepare_image(self):
        w, h = int(self.width()), int(self.height())
        if w < 2 or h < 2:
            return
        ordered = np.concatenate((self.data[:, self._write:], self.data[:, :self._write]), axis=1)
        channels = self._channel_count
        # Bound total polygon vertices as channel count grows. Min/max buckets
        # preserve peaks while keeping the 16-channel monitor responsive.
        count = max(1, min(w//2, 2000//channels))
        starts = np.linspace(0, 4000, count+1, dtype=int)[:-1]
        # One native NumPy pass per bound, across all channels.
        low = np.minimum.reduceat(ordered, starts, axis=1)
        high = np.maximum.reduceat(ordered, starts, axis=1)
        xs = np.repeat(np.linspace(0, w-1, count), 2)
        extrema = np.stack((low, high), axis=-1).reshape(channels, -1)
        image = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
        image.fill(QColor('#141e29'))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setPen(QPen(QColor('#23323e'), 1))
        for x in range(0, w, 80):
            painter.drawLine(x, 0, x, h)
        colors = [
            "#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF",
            "#D7BAFF", "#FFC4E1", "#C4F0FF", "#D5F5C8", "#F5D0A9",
            "#F6C6D8", "#C9C9FF", "#B8E0D2", "#FFE5B4", "#DCC6E0",
            "#A8DADC", "#F4ACB7", "#CDEAC0", "#F9D5E5", "#BDE0FE",
            "#E2C2FF", "#FFD6A5", "#CAFFBF", "#FDFFB6", "#9BF6FF",
            "#FFC6FF", "#E4C1F9", "#C1FBA4", "#FAD2E1", "#CDE7F0"
        ]
        for channel in range(channels):
            color = colors[channel]
            center = (channel+.5)*h/channels
            painter.save()
            painter.setClipRect(QRectF(0, channel*h/channels, w, h/channels))
            painter.setPen(QPen(QColor('#283641'), 1))
            painter.drawLine(0, int(center), w, int(center))
            if self._data_type == "emg":
                ys = center - extrema[channel]*h/(2*channels*0.025)
            else:
                ys = center - extrema[channel]*h/(2*channels*2)
            polygon = QPolygonF([QPointF(float(x), float(y)) for x, y in zip(xs, ys)])
            painter.setPen(QPen(QColor(color), 1))
            painter.drawPolyline(polygon)
            painter.restore()
        painter.end()
        self._image = image

    def paint(self, painter: QPainter):
        if not self._image.isNull():
            painter.drawImage(QPointF(0, 0), self._image)
