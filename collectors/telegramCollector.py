from core.collector import Collector
import os
import time
import asyncio

from registry.permissionsRegistry import has_permission, is_chat_allowed
from telegram import Update # type: ignore
from telegram.ext import ( # type: ignore
    Application,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler,
)

CONFIRM_TIMEOUT_SECONDS = 30

# Commands listed here require /confirm_<command> before they're published.
CONFIRMABLE_COMMANDS = {"reboot"}

class TelegramCollector(Collector):
    def __init__(self, bus):
        super().__init__(bus)

        self.pending_confirmations = {}  # user_id -> (command, args, chat_id, requested_at)

        self.application = Application.builder().token(
            os.getenv("TELEGRAM_TOKEN")
        ).build()

        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message)
        )

        self.application.add_handler(CommandHandler("status", self.on_command))
        self.application.add_handler(CommandHandler("battery", self.on_command))
        self.application.add_handler(CommandHandler("sessions", self.on_command))

        self.application.add_handler(CommandHandler("reboot", self.on_command))
        self.application.add_handler(CommandHandler("confirm_reboot", self.on_confirm_command))

        self.application.add_handler(
            CommandHandler("whoami", self.on_whoami)
        )


    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    async def on_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"user_id: {update.effective_user.id}\nchat_id: {update.effective_chat.id}"
        )

    async def on_command(self, update, context):
        command = update.message.text.lstrip("/")

        if not has_permission(update.effective_user.id, command):
            await update.message.reply_text("You are not allowed to use this command.")
            return

        if not is_chat_allowed(update.effective_chat.id):
            await update.message.reply_text("This chat is not allowed to use this bot.")
            return

        if command in CONFIRMABLE_COMMANDS:
            self.pending_confirmations[update.effective_user.id] = (
                command, context.args, update.effective_chat.id, time.monotonic()
            )
            await update.message.reply_text(
                f"Are you sure you want to run /{command}? This action cannot be undone. "
                f"Type /confirm_{command} within {CONFIRM_TIMEOUT_SECONDS}s to proceed."
            )
            return

        self.bus.publish("CommandReceived", {
            "command": command,
            "chat_id": update.effective_chat.id,
            "args": context.args,
        })

    async def on_confirm_command(self, update, context):
        command = update.message.text.lstrip("/").removeprefix("confirm_")

        if not has_permission(update.effective_user.id, command):
            await update.message.reply_text("You are not allowed to use this command.")
            return

        if not is_chat_allowed(update.effective_chat.id):
            await update.message.reply_text("This chat is not allowed to use this bot.")
            return

        pending = self.pending_confirmations.pop(update.effective_user.id, None)

        if pending is None or pending[0] != command:
            await update.message.reply_text(f"No pending /{command} request. Send /{command} first.")
            return

        _, args, chat_id, requested_at = pending

        if time.monotonic() - requested_at > CONFIRM_TIMEOUT_SECONDS:
            await update.message.reply_text(f"Confirmation expired. Send /{command} again.")
            return

        self.bus.publish("CommandReceived", {
            "command": command,
            "chat_id": chat_id,
            "args": args,
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