from core.bus import Bus

class Notifier:
    def __init__(self, bus: Bus):
        self.bus = bus

    async def send_message(self, message, chat_id=None):
        # Implement the logic to send a notification (e.g., email, SMS, etc.)
        print(f"Sending notification: {message}")