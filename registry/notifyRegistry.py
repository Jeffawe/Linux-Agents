from core import Bus, Notifier
from notifiers import TelegramNotifier, DiscordNotifier

class NotifyRegistry:
    def __init__(self, bus: Bus):
        self.bus = bus
        self._notifiers: dict[str, type[Notifier]] = {
            "telegram": TelegramNotifier,
            "discord": DiscordNotifier,
            "default": TelegramNotifier,  # Default notifier if none specified
        }

    def get(self, key: str) -> Notifier | None:
        cls = self._notifiers.get(key)

        if not cls:
            return None

        return cls(self.bus)