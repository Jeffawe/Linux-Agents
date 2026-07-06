from core.action import Action
from registry.notifyRegistry import NotifyRegistry 

class NotifyAction(Action):
    def __init__(self, bus):
        super().__init__(bus)

        self.bus.subscribe("Notify", self.handle)
        self.bus.subscribe("PowerChanged", self.handle)
        self.registry = NotifyRegistry(bus)

    async def handle(self, context):
        if not context:
            return  # No context provided, do nothing
        
        message = context.get("message")

        if not message:
            return  # No message provided, do nothing
        
        channel = context.get("channel", "telegram")  # default to telegram if not specified

        notifier = self.registry.get(channel)
        if not notifier:
            return  # No notifier found for the specified channel 
        else:
            await notifier.send_message(message)