import asyncio
import inspect


class Bus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, callback):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type, callback):
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(callback)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

    def publish(self, event_type, data):
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                if inspect.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)