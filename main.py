import asyncio
import signal

from dotenv import load_dotenv # type: ignore

from core import Bus, Collector, Action, Notifier, Rule
from core.watchdog import notify_ready, run_watchdog
from data.stateStore import StateStore
from loader import load_plugins

load_dotenv()


async def main():
    bus = Bus()
    state_store = StateStore(bus)

    collectors = load_plugins("collectors", Collector, bus)
    actions = load_plugins("actions", Action, bus)
    notifiers = load_plugins("notifiers", Notifier, bus)
    rules = load_plugins("rules", Rule, bus, state_store)

    stopping = asyncio.Event()
    tasks = []

    async def shutdown():
        print("\nShutting down...")

        # SystemStopping has a synchronous subscriber that records the clean
        # shutdown marker, so it runs inline right here.
        bus.publish("SystemStopping", {
            "message": "Agent system shutting down..."
        })

        for c in collectors:
            c.stop()

        stopping.set()

    loop = asyncio.get_running_loop()

    # SIGINT is what the unit sends (KillSignal); SIGTERM covers everything else,
    # so an unhandled signal cannot skip the clean shutdown marker.
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    bus.publish("SystemBooting", {
        "message": "Agent system is starting..."
    })

    for collector in collectors:
        tasks.append(asyncio.create_task(collector.start()))

    bus.publish("SystemStarted", {
        "message": "Agent system started successfully"
    })

    notify_ready()
    tasks.append(asyncio.create_task(run_watchdog(collectors, stopping)))

    await stopping.wait()

    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
