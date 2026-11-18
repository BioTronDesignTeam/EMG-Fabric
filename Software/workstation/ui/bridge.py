from PySide6.QtCore import QObject, Property, Signal, Slot


class WorkspaceBridge(QObject):
    runningChanged = Signal()

    def __init__(self, source, hand=None):
        super().__init__()
        self.source = source
        self.hand = hand
        self._running = True

    @Property(bool, notify=runningChanged)
    def running(self):
        return self._running

    @Slot()
    def toggleRunning(self):
        self._running = not self._running
        self.source.set_running(self._running)
        if self.hand is not None:
            self.hand.setRunning(self._running)
        self.runningChanged.emit()
