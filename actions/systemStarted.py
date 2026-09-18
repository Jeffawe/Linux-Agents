from core.action import Action
from data.shutdownMarker import consume_clean_shutdown, mark_clean_shutdown

class SystemStarted(Action):
    def __init__(self, bus):
        super().__init__(bus)
        self.bus.subscribe("SystemStarted", self.handle)

        # Deliberately synchronous: Bus.publish runs sync subscribers inline, so
        # the marker lands on disk during shutdown() rather than in a task that
        # may never be scheduled before the process exits.
        self.bus.subscribe("SystemStopping", self.on_stopping)

    def on_stopping(self, context):
        mark_clean_shutdown()

    async def handle(self, context):
        # A deploy, a `systemctl restart` or any other intentional stop leaves a
        # marker behind. Only restarts we did not ask for are worth a message.
        if consume_clean_shutdown():
            print("✅ Agent system started successfully (clean restart, staying quiet)")
            return

        print("⚠️  Agent system started after an unclean shutdown")

        self.bus.publish("Notify", {
            "message": "⚠️ Agent system restarted unexpectedly (no clean shutdown recorded).",
            "channel": "default"
        })
