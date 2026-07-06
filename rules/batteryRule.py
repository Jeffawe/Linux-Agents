from core.rule import Rule, Bus
from data.stateStore import StateStore

class BatteryRule(Rule):
    def __init__(self, bus: Bus, state: StateStore):
        super().__init__(bus, state)

        self.bus.subscribe("BatteryChanged", self.handle)

    async def handle(self, context):
        if not context:
            return  # No context provided, do nothing
        
        current_value = context.get("value")

        if current_value is None:
            return  # No value provided, do nothing

        if current_value < 20 and not self.triggered:
            self.triggered = True
            self.bus.publish("Notify", {"message": "Battery is low!", "channel": "default"})

        elif current_value >= 25:
            self.triggered = False