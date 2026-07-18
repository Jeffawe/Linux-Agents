from core import Bus, Command
from data.stateStore import StateStore

class BatteryCommand(Command):
    def __init__(self, bus: Bus, state: StateStore):
        super().__init__(bus, state)

    async def handle(self, data):
        if not data:
            return  # No data provided, do nothing

        command = data.get("command")

        if not command:
            return  # No command provided, do nothing

        chat_id = data.get("chat_id")

        if self.state is None:
            return  # No state store available, do nothing
        
        battery = self.state.get("battery")
        ac = self.state.get("ac")

        if battery is None:
            return  # No battery value available, do nothing

        if ac is not None:
            ac_message = "Charging" if ac else "Discharging"
        else:
            ac_message = ""

        print(f"Battery: {battery}% ({ac_message})")

        self.bus.publish("Notify", {
            "channel": "telegram",
            "chat_id": chat_id,
            "message": f"Battery: {battery}% ({ac_message})"
        })