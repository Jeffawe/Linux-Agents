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

RECONNECT_DELAY_SECONDS = 10

# How often to prove to ourselves that the polling connection still works.
HEALTH_PROBE_INTERVAL_SECONDS = 60

# How long probes may keep failing before the watchdog restarts the process.
DEFAULT_HEALTH_TIMEOUT_SECONDS = 900

class TelegramCollector(Collector):
    def __init__(self, bus):
        super().__init__(bus)

        self.pending_confirmations = {}  # user_id -> (command, args, chat_id, requested_at)

        self.health_timeout_seconds = int(
            os.getenv("TELEGRAM_HEALTH_TIMEOUT") or DEFAULT_HEALTH_TIMEOUT_SECONDS
        )

        self.application = self._build_application()

    def health_timeout(self):
        return self.health_timeout_seconds

    def _build_application(self):
        application = Application.builder().token(
            os.getenv("TELEGRAM_TOKEN")
        ).build()

        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message)
        )

        application.add_handler(CommandHandler("status", self.on_command))
        application.add_handler(CommandHandler("battery", self.on_command))
        application.add_handler(CommandHandler("sessions", self.on_command))

        application.add_handler(CommandHandler("reboot", self.on_command))
        application.add_handler(CommandHandler("confirm_reboot", self.on_confirm_command))

        application.add_handler(CommandHandler("rustdesk_start", self.on_command))
        application.add_handler(CommandHandler("rustdesk_restart", self.on_command))

        application.add_handler(
            CommandHandler("whoami", self.on_whoami)
        )

        return application


    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pass

    async def on_whoami(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            f"user_id: {update.effective_user.id}\nchat_id: {update.effective_chat.id}"
        )

    async def on_command(self, update, context):
        command = update.message.text.split()[0].lstrip("/").split("@")[0]

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
        command = update.message.text.split()[0].lstrip("/").split("@")[0].removeprefix("confirm_")

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
        while self.running:
            try:
                # Working the reconnect path counts as alive: that loop already
                # heals itself, so the watchdog should leave it be.
                self.mark_healthy()

                await self.application.initialize()
                await self.application.start()
                await self.application.updater.start_polling()

                self.mark_healthy()
            except Exception as e:
                print(f"Error starting TelegramCollector: {e}. Retrying in {RECONNECT_DELAY_SECONDS}s")
                self.application = self._build_application()
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                continue

            await self._poll_until_stopped()

            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def _poll_until_stopped(self):
        """Idle while the updater polls, probing the API as we go.

        This is the case the 6h RuntimeMaxSec restart existed for: the updater
        still reports itself as running while its socket quietly stops
        delivering updates. Nothing raises, so the only way to notice is to ask
        Telegram something ourselves and watch the answers stop coming.
        """
        seconds_since_probe = 0

        while self.running:
            await asyncio.sleep(1)
            seconds_since_probe += 1

            if seconds_since_probe < HEALTH_PROBE_INTERVAL_SECONDS:
                continue

            seconds_since_probe = 0

            try:
                await self.application.bot.get_me()
                self.mark_healthy()
            except Exception as e:
                # Not fatal on its own - only a run of these outlasting
                # health_timeout() stops the watchdog pings.
                print(f"Telegram health probe failed: {e}")

    def stop(self):
        self.running = False