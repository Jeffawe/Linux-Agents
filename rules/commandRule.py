from core import Bus, Rule
from data.stateStore import StateStore
from registry.commandRegistry import CommandRegistry

class CommandRule(Rule):
    def __init__(self, bus: Bus, state: StateStore):
        super().__init__(bus, state)

        self.registry = CommandRegistry(bus, state)

        # Subscribe to the "CommandReceived" event to update the state_store
        self.bus.subscribe("CommandReceived", self.handle)

    async def handle(self, context):
        if not context or "command" not in context:
            return

        command = context["command"]
        chat_id = context.get("chat_id", None)

        data = {
            "command": command,
            "chat_id": chat_id,
            "timestamp": context.get("timestamp", None)
        }

        print(f"CommandRule: Received command: {command} with data: {data}")

        command_system = self.registry.get(command)
        if command_system:
            await command_system.handle(data)


