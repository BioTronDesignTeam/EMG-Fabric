import numpy as np
from PySide6.QtCore import QPointF, Property, QRectF, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from PySide6.QtQuick import QQuickPaintedItem


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
        self._write = 0
        self._image = QImage()
        self._dirty = True
        self.widthChanged.connect(self._invalidate)
        self.heightChanged.connect(self._invalidate)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.consume)
        self.timer.start(33)

    def _invalidate(self):
        self._dirty = True

    @Property(int, notify=channelCountChanged)
    def channelCount(self):
        return self._channel_count

    @channelCount.setter
    def channelCount(self, count):
        if count not in (2, 4, 8, 16) or count == self._channel_count:
            return
        self._channel_count = count
        self.data = np.zeros((count, 4000))
        self._write = 0
        self._dirty = True
        self.channelCountChanged.emit()

    def consume(self):
        changed = False
        if self.bus:
            for block in self.bus.drain():
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
        colors = ['#48d9cb', '#66b8f7', '#b097ee', '#e1b56b',
                  '#ed8c9d', '#7fd48a', '#7bd1ea', '#d3a2cf',
                  '#c5d779', '#e5a17b', '#83a7ed', '#d7bce9',
                  '#67bfae', '#ddca9a', '#aecee8', '#d5a5ac']
        for channel in range(channels):
            color = colors[channel]
            center = (channel+.5)*h/channels
            painter.save()
            painter.setClipRect(QRectF(0, channel*h/channels, w, h/channels))
            painter.setPen(QPen(QColor('#283641'), 1))
            painter.drawLine(0, int(center), w, int(center))
            ys = center - extrema[channel]*h/(2*channels*.025)
            polygon = QPolygonF([QPointF(float(x), float(y)) for x, y in zip(xs, ys)])
            painter.setPen(QPen(QColor(color), 1))
            painter.drawPolyline(polygon)
            painter.restore()
        painter.end()
        self._image = image

    def paint(self, painter: QPainter):
        if not self._image.isNull():
            painter.drawImage(QPointF(0, 0), self._image)
