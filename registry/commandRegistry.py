from core import Bus, Command
from data.stateStore import StateStore
from commands import BatteryCommand, SessionsCommand, RebootCommand, RustdeskCommand

class CommandRegistry:
    def __init__(self, bus: Bus, state: StateStore):
        self.bus = bus
        self.state = state
        self._commands: dict[str, type[Command]] = {
            "battery": BatteryCommand,
            "sessions": SessionsCommand,
            "reboot": RebootCommand,
            "rustdesk_start": RustdeskCommand,
            "rustdesk_restart": RustdeskCommand,
        }

    def get(self, key: str) -> Command | None:
        cls = self._commands.get(key)

        if not cls:
            return None

        return cls(self.bus, self.state)