import asyncio

from core import Bus, Command
from data.stateStore import StateStore

REBOOT_DELAY_SECONDS = 3  # gives the "rebooting now" notification time to actually send

class RebootCommand(Command):
    def __init__(self, bus: Bus, state: StateStore):
        super().__init__(bus, state)

    async def handle(self, data):
        if not data:
            return  # No data provided, do nothing

        command = data.get("command")

        if not command:
            return  # No command provided, do nothing

        chat_id = data.get("chat_id")

        self.bus.publish("Notify", {
            "channel": "telegram",
            "chat_id": chat_id,
            "message": "Rebooting now..."
        })

        await asyncio.sleep(REBOOT_DELAY_SECONDS)

        try:
            proc = await asyncio.create_subprocess_exec("systemctl", "reboot")
            await proc.wait()

            if proc.returncode != 0:
                raise RuntimeError(f"systemctl reboot exited with code {proc.returncode}")
        except (FileNotFoundError, RuntimeError) as e:
            self.bus.publish("Notify", {
                "channel": "telegram",
                "chat_id": chat_id,
                "message": f"Reboot failed: {e}"
            })