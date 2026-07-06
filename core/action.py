from core.bus import Bus

class Action:
    def __init__(self, bus: Bus):
        self.bus = bus

    async def handle(self, context):
        return NotImplementedError("Subclasses must implement the handle method.")