import os


def _parse_ids(env_var):
    raw = os.getenv(env_var, "")
    return {int(v) for v in raw.split(",") if v.strip()}


USER_ROLES = {}
for user_id in _parse_ids("ADMIN_USER_IDS"):
    USER_ROLES[user_id] = "admin"
for user_id in _parse_ids("VIEWER_USER_IDS"):
    USER_ROLES[user_id] = "viewer"

ROLE_PERMISSIONS = {
    "admin": {
        "status",
        "battery",
        "sessions",
        "reboot",
        "rustdesk_start",
        "rustdesk_restart",
    },
    "viewer": {
        "status",
        "battery",
        "sessions",
    },
}

ALLOWED_CHATS = _parse_ids("ALLOWED_CHAT_IDS")

def has_permission(user_id, command):
    role = USER_ROLES.get(user_id)
    if not role:
        return False
    return command in ROLE_PERMISSIONS.get(role, set())

def is_chat_allowed(chat_id):
    return chat_id in ALLOWED_CHATS