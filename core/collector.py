from core.bus import Bus

class Collector:
    def __init__(self, bus: Bus):
        self.data = []
        self.bus = bus
        self.running = True

    def collect(self, item):
        self.data.append(item)

    def get_data(self):
        return self.data
    
    async def start(self):
        raise NotImplementedError("Subclasses must implement the start method.")
    
    def stop(self):
        self.running = False