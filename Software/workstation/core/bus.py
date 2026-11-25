from queue import Queue
from threading import Lock
from weakref import ref

from .messages import SignalBlock


class SignalBus:
    """Broadcast signal blocks to independent subscriber queues."""

    def __init__(self):
        self._subscribers = []
        self._lock = Lock()

    def subscribe(self):
        subscriber = Queue()
        with self._lock:
            self._subscribers = [
                subscriber_ref
                for subscriber_ref in self._subscribers
                if subscriber_ref() is not None
            ]
            self._subscribers.append(ref(subscriber))
        return subscriber

    def publish(self, block: SignalBlock):
        with self._lock:
            active_subscribers = []
            for subscriber_ref in self._subscribers:
                subscriber = subscriber_ref()
                if subscriber is not None:
                    subscriber.put_nowait(block)
                    active_subscribers.append(subscriber_ref)
            self._subscribers = active_subscribers
