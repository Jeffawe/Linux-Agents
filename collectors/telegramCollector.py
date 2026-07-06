from core.collector import Collector
import os
import asyncio
from telegram import Update # type: ignore
from telegram.ext import ( # type: ignore
    Application,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler,
)

class TelegramCollector(Collector):
    def __init__(self, bus):
        super().__init__(bus)

        self.application = Application.builder().token(
            os.getenv("TELEGRAM_TOKEN")
        ).build()

        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message)
        )

        self.application.add_handler(
            CommandHandler("battery", self.on_command)
        )


    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    async def on_command(self, update, context):
        print(f"Received command: {update.message.text.lstrip('/')} from chat_id: {update.effective_chat.id}")
        self.bus.publish("CommandReceived", {
            "command": update.message.text.lstrip("/"),
            "chat_id": update.effective_chat.id,
            "args": context.args,
        })
    
    async def start(self):
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        while self.running:
            await asyncio.sleep(1)

        await self.application.updater.stop()
        await self.application.stop()
        await self.application.shutdown()

    def stop(self):
        self.running = False