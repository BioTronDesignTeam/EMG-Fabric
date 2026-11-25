from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot
models = ["coughing baby","hydrogen bomb"]

class MLController(QObject):
    changed = Signal()
    def __init__(self):
        super().__init__()
        self._model_id = "coughing baby"
        self._modelIndex = 0
        self._pool = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix='ml-inference'
        )
        self._timer=QTimer(self);self._timer.timeout.connect(self._poll);self._timer.start(16)
        

    def _poll(self):
        pass

    @Property(int,notify=changed)
    def modelIndex(self):
        return self._modelIndex
    @Property(str,notify=changed)
    def model_id(self):
        return self._model_id

    
    @Slot(str)
    def setModel(self,model_id):        
        self._model_id = model_id
        self._modelIndex = models.index(model_id)
        self.changed.emit()
    
    def close(self):
        self._timer.stop()
        self._pool.shutdown(wait=True, cancel_futures=True)