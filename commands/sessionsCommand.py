import subprocess

from core import Bus, Command
from data.stateStore import StateStore

SESSION_PROPERTIES = [
    "Name", "State", "IdleHint", "Seat", "TTY", "Type", "Class",
    "Remote", "RemoteHost", "Timestamp",
]

GUI_SESSION_TYPES = {"wayland", "x11"}

class SessionsCommand(Command):
    def __init__(self, bus: Bus, state: StateStore):
        super().__init__(bus, state)

    def _list_session_ids(self):
        result = subprocess.run(
            ["loginctl", "list-sessions", "--no-legend"],
            capture_output=True, text=True, check=True
        )
        return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]

    def _session_info(self, session_id):
        args = ["loginctl", "show-session", session_id]
        for prop in SESSION_PROPERTIES:
            args += ["-p", prop]

        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return dict(
            line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
        )

    def _format_session(self, info):
        idle = info.get("IdleHint") == "yes"
        gui = info.get("Type") in GUI_SESSION_TYPES

        lines = [
            f"User: {info.get('Name', '?')}",
            f"Status: {'idle' if idle else 'active'}",
            f"GUI: {'active' if gui else 'no'}" + (f" ({info['Seat']})" if gui and info.get("Seat") else ""),
        ]

        if info.get("Remote") == "yes":
            host = info.get("RemoteHost")
            lines.append(f"Remote: yes" + (f" (via {host})" if host else ""))

        if info.get("Timestamp"):
            lines.append(f"Logged in since: {info['Timestamp']}")

        return "\n".join(lines)

    async def handle(self, data):
        if not data:
            return  # No data provided, do nothing

        command = data.get("command")

        if not command:
            return  # No command provided, do nothing

        chat_id = data.get("chat_id")

        try:
            session_ids = self._list_session_ids()
            infos = [self._session_info(sid) for sid in session_ids]
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.bus.publish("Notify", {
                "channel": "telegram",
                "chat_id": chat_id,
                "message": f"Could not fetch sessions: {e}"
            })
            return

        # "manager" sessions are systemd's own per-user background instance,
        # not an actual login - not useful to show here.
        blocks = [
            self._format_session(info) for info in infos if info.get("Class") != "manager"
        ]

        message = "\n\n".join(blocks) if blocks else "No active sessions."

        print(f"Sessions:\n{message}")

        self.bus.publish("Notify", {
            "channel": "telegram",
            "chat_id": chat_id,
            "message": f"Sessions:\n{message}"
        })