from telegram import Bot
from core.notifier import Notifier
import os

class TelegramNotifier(Notifier):
    def __init__(self, bus):
        super().__init__(bus)
        self.bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    async def send_message(self, message, chat_id=None):
        await self.bot.send_message(
            chat_id=chat_id or self.chat_id,
            text=message
        )