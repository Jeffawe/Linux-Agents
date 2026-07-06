from core import Bus
from data.stateStore import StateStore

class Command:
    def __init__(self, bus: Bus, state: StateStore):
        self.bus = bus
        self.state = state

    async def handle(self, context):
        return NotImplementedError("Subclasses must implement the handle method.")