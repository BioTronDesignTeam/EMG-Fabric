from queue import Empty
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, QUrl
from .inference import VEMG2POSEInference

class MLController(QObject):
    bus = None
    modelchanged = Signal()
    def __init__(self):
        super().__init__()
        self._model_id:str = "tracking_vemg2pose"
        self._ckpt = ""
        self._models = ["tracking_vemg2pose","regression_vemg2pose"]
        self._modelIndex: int = 0
        self.module = VEMG2POSEInference()
        self._queue = self.bus.subscribe()
        # self._pool = ThreadPoolExecutor(
        #     max_workers=1,
        #     thread_name_prefix='ml-inference'
        # ) idk what this is used for
        self._timer=QTimer(self);self._timer.timeout.connect(self.consume);self._timer.start(33)

    def consume(self):
        pass
        # changed = False
        # while True:
            # try:
                # block = self._queue.get_nowait()
        #     except Empty:
        #         break
        #     if self._data_type == "joint_angles":
        #         if block.labels is None:
        #             continue
        #         samples = block.labels[:, -4000:]
        #     else:
        #         samples = block.samples[:, -4000:]
        #     # Discard queued blocks from the previous channel layout.
        #     if samples.shape[0] != self._channel_count:
        #         continue
        #     n = samples.shape[1]
        #     first = min(n, 4000-self._write)
        #     self.data[:, self._write:self._write+first] = samples[:, :first]
        #     if first < n:
        #         self.data[:, :n-first] = samples[:, first:]
        #     self._write = (self._write+n) % 4000
        #     changed = True
        # if (changed or self._dirty) and self.isVisible():
        #     self.prepare_image()
        #     self.update()
        #     self._dirty = False

    @Property(int,notify=modelchanged)
    def modelIndex(self):
        return self._modelIndex
    @Property(str,notify=modelchanged)
    def model_id(self):
        return self._model_id
    @Property(list,constant=True)
    def models(self):
        return self._models
    @Property(str,notify=modelchanged)
    def checkpoint(self):
        return self._ckpt
    
    @Slot(str)
    def setModel(self,model_id):        
        self._model_id = model_id
        self._modelIndex = self._models.index(model_id)
        self.modelchanged.emit()
        self.load_model()

    @Slot(str)
    def loadcheckpointFile(self,url):
            self._ckpt = QUrl(url).toLocalFile()
            self.modelchanged.emit()
            self.load_model()

    def load_model(self):
        self.module.load_model(self._model_id,self._ckpt)

    
    def close(self):
        self._timer.stop()
        #self._pool.shutdown(wait=True, cancel_futures=True)