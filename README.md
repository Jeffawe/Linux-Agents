# Linux Agents

A small asyncio, event-driven agent that watches system state (battery, power, uptime, sessions) and lets you control the machine via Telegram commands (reboot, status checks, etc.), with Discord/Telegram notifications.

## Architecture: everything is events on a `Bus`

There's no central dispatcher process. `core/bus.py` (`Bus`) is a plain pub/sub map: `subscribe(event_type, callback)` / `publish(event_type, data)`. Every piece of the app wires itself up by subscribing to the events it cares about.

`loader.py` (`load_plugins`) scans a folder, finds subclasses of a given base, and instantiates each with the `bus`. Each plugin subscribes to the bus **inside its own `__init__`** — nothing is registered centrally. `main.py` just calls `load_plugins` for `collectors/`, `rules/`, `actions/`, `notifiers/` in that order, plus publishes `SystemBooting` / `SystemStarted` / `SystemStopping` itself.

### The flow

```
Collectors  →  publish raw events  →  Rules  →  react / publish new events  →  Actions & Notifiers
```

1. **Collectors** (`collectors/`, base `core/collector.py`) — producers. They watch the outside world and publish events onto the bus.
   - `telegramCollector.py` — listens for Telegram bot commands, checks `registry/permissionsRegistry.py` (admin/viewer roles, allowed chat IDs), handles confirmation for destructive commands, then publishes **`CommandReceived`**.
   - `powerCollector.py` — polls `/sys/class/power_supply/...`, publishes **`StateUpdated`**, **`PowerChanged`**, **`BatteryChanged`**.

2. **Rules** (`rules/`, base `core/rule.py`) — the business logic layer. They subscribe to collector events, hold small bits of state, and either publish a new event or trigger a command.
   - `batteryRule.py` — subscribes to `BatteryChanged`; publishes **`Notify`** when battery drops below 20%, resets when it recovers above 25%.
   - `commandRule.py` — subscribes to `CommandReceived`; looks the command name up in `registry/commandRegistry.py` and calls the matching **Command**. This is the bridge between events and commands.

3. **Commands** (`commands/`, base `core/command.py`) — do the actual work for a specific action (`rebootCommand.py`, `batteryCommand.py`, `sessionsCommand.py`, `rustdeskCommand.py`). Looked up by name via `CommandRegistry`, invoked as `Command.handle(data)`. They typically publish their own `Notify` events to report results/errors — they don't talk to notifiers directly.

4. **Actions** (`actions/`, base `core/action.py`) — subscribe to system/lifecycle events and react.
   - `notifyAction.py` — subscribes to `Notify` / `PowerChanged`, looks up the right channel in `registry/notifyRegistry.py`, and forwards to the matching **Notifier**.
   - `systemStarted.py` — reacts to `SystemStarted` to send a startup message.

5. **Notifiers** (`notifiers/`) — `telegram.py`, `discord.py`. Dumb senders, invoked only by `notifyAction.py`.

6. **State** — `data/stateStore.py` (`StateStore`) subscribes to `StateUpdated` and keeps the latest snapshot, passed into Rules/Commands that need current values instead of re-polling.

### Registries (lookup tables, not event-driven)

- `registry/commandRegistry.py` — command name → `Command` class.
- `registry/notifyRegistry.py` — channel name → `Notifier` instance.
- `registry/permissionsRegistry.py` — role + allowed-chat-id checks, env-driven (`ADMIN_USER_IDS`, `VIEWER_USER_IDS`, `ALLOWED_CHAT_IDS`).

### Adding something new

- New thing to watch → add a **Collector** that publishes an event.
- New reaction to an existing event → add a **Rule**.
- New user-triggered action (e.g. a Telegram command) → add a **Command**, register it in `commandRegistry.py`.
- New way to be notified → add a **Notifier**, register it in `notifyRegistry.py`.

No wiring beyond dropping the file in the right folder — `load_plugins` and the base class's own `__init__` subscription handle the rest.
