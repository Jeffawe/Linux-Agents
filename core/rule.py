from core.bus import Bus
from data.stateStore import StateStore

class Rule:
    def __init__(self, bus: Bus, state: StateStore):
        self.bus = bus
        self.state = state
        self.triggered = False

    async def handle(self, context):
        return NotImplementedError("Subclasses must implement the handle method.")