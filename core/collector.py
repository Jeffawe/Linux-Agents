import time

from core.bus import Bus

class Collector:
    def __init__(self, bus: Bus):
        self.data = []
        self.bus = bus
        self.running = True
        self.last_healthy_at = time.monotonic()

    def collect(self, item):
        self.data.append(item)

    def get_data(self):
        return self.data

    def mark_healthy(self):
        """Record a beat. Collectors call this whenever they make real progress."""
        self.last_healthy_at = time.monotonic()

    def health_timeout(self):
        """Seconds without a beat before the watchdog should give up on us.

        None means this collector never reports itself unhealthy.
        """
        return None

    def is_healthy(self):
        timeout = self.health_timeout()

        if timeout is None:
            return True

        # time.monotonic() excludes time spent suspended, so a laptop waking
        # from sleep does not look like a stall.
        return (time.monotonic() - self.last_healthy_at) <= timeout

    async def start(self):
        raise NotImplementedError("Subclasses must implement the start method.")

    def stop(self):
        self.running = False
