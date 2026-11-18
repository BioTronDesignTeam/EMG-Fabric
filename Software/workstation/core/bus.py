from queue import Empty, Full, Queue

from .messages import SignalBlock


class SignalBus:
    """Bounded display subscription: stale display blocks are discarded."""

    def __init__(self):
        self._queue = Queue(maxsize=8)

    def publish(self, block: SignalBlock):
        try:
            self._queue.put_nowait(block)
        except Full:
            try:
                self._queue.get_nowait()
            except Empty:
                pass
            self._queue.put_nowait(block)

    def drain(self):
        while True:
            try:
                yield self._queue.get_nowait()
            except Empty:
                return
