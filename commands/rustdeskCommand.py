import asyncio
import pwd

from core import Bus, Command
from data.stateStore import StateStore

RUSTDESK_SERVICE = "rustdesk"

# RustDesk runs as a systemd --user unit under this account, not system-wide,
# so it has to be controlled via sudo -u rather than a plain systemctl call.
REMOTE_USER = "remoteuser"

# Absolute paths so this doesn't depend on PATH being set a particular way -
# matches the exact paths the sudoers NOPASSWD rule for serveruser is scoped to.
SUDO_BIN = "/usr/bin/sudo"
ENV_BIN = "/usr/bin/env"
SYSTEMCTL_BIN = "/usr/bin/systemctl"

# Telegram command name -> systemctl verb
ACTIONS = {
    "rustdesk_start": "start",
    "rustdesk_restart": "restart",
}

class RustdeskCommand(Command):
    def __init__(self, bus: Bus, state: StateStore):
        super().__init__(bus, state)

    async def handle(self, data):
        if not data:
            return  # No data provided, do nothing

        command = data.get("command")

        if not command:
            return  # No command provided, do nothing

        action = ACTIONS.get(command)

        if not action:
            return  # Unknown command, do nothing

        chat_id = data.get("chat_id")

        try:
            uid = pwd.getpwnam(REMOTE_USER).pw_uid

            proc = await asyncio.create_subprocess_exec(
                SUDO_BIN, "-n", "-u", REMOTE_USER,
                ENV_BIN, f"XDG_RUNTIME_DIR=/run/user/{uid}",
                SYSTEMCTL_BIN, "--user", action, RUSTDESK_SERVICE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                detail = stderr.decode().strip() or f"exit code {proc.returncode}"
                raise RuntimeError(f"systemctl --user {action} {RUSTDESK_SERVICE} (as {REMOTE_USER}) failed: {detail}")

            message = f"RustDesk {action}ed."
        except (FileNotFoundError, RuntimeError, KeyError) as e:
            message = f"RustDesk {action} failed: {e}"

        self.bus.publish("Notify", {
            "channel": "telegram",
            "chat_id": chat_id,
            "message": message
        })
