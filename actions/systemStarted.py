from core.action import Action

class SystemStarted(Action):
    def __init__(self, bus):
        super().__init__(bus)
        self.bus.subscribe("SystemStarted", self.handle)

    async def handle(self, context):
        # Handle the system started event
        print("✅ Agent system started successfully")

        self.bus.publish("Notify", {
            "message": "Agent system started successfully",
            "channel": "default"
        })