from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from ..ml.data import EMGData, FileSource

class WorkspaceBridge(QObject):
    runningChanged = Signal()
    recordingLoaded = Signal()

    def __init__(self, source, hand=None):
        super().__init__()
        self.source = source
        self.hand = hand
        self._running = True
        self.recording = None
        self.file_source = None
        self._filename = ""

    @Property(bool, notify=runningChanged)
    def running(self):
        return self._running
    
    @Property(str, notify=recordingLoaded)
    def filename(self):
            return self._filename
    @Slot()
    def toggleRunning(self):
        self._running = not self._running

        self.source.set_running(
            self._running if self.file_source is None else False
        )

        if self.file_source is not None:
            self.file_source.set_running(self._running)

        if self.hand is not None:
            self.hand.setRunning(self._running)

        self.runningChanged.emit()

    @Slot()
    def useSyntheticSource(self):
        if self.file_source is not None:
            self.file_source.set_running(False)
            self.file_source.close()
            self.file_source = None
            self.recording = None
        self.source.set_running(self._running)

    @Slot(str)
    def loadSignalFile(self, url):
        """
        Currently Loads hdf5 file used by emg2pose
        """

        path = QUrl(url).toLocalFile()
        self.source.set_running(False)
        if self.file_source is not None:
            self.file_source.set_running(False)
            self.file_source.close()
        
        self.recording = EMGData(Path(path))
        self._filename = self.recording.filename
        self.recordingLoaded.emit()

        self.file_source = FileSource(
            self.source.bus,
            self.recording
        )
        self.file_source.set_running(self._running)
        self.file_source.start()
