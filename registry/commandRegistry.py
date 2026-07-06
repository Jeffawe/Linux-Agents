from core import Bus, Command
from data.stateStore import StateStore
from commands import BatteryCommand

class CommandRegistry:
    def __init__(self, bus: Bus, state: StateStore):
        self.bus = bus
        self.state = state
        self._commands: dict[str, type[Command]] = {
            "battery": BatteryCommand
        }

    def get(self, key: str) -> Command | None:
        cls = self._commands.get(key)

        if not cls:
            return None

        return cls(self.bus, self.state)