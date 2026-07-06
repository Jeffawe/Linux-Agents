import asyncio
import signal

from dotenv import load_dotenv # type: ignore

from core import Bus, Collector, Action, Notifier, Rule
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

    running = True
    tasks = []

    async def shutdown():
        nonlocal running

        print("\nShutting down...")

        bus.publish("SystemStopping", {
            "message": "Agent system shutting down..."
        })

        for c in collectors:
            c.stop()

        running = False

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown()))

    bus.publish("SystemBooting", {
        "message": "Agent system is starting..."
    })

    for collector in collectors:
        tasks.append(asyncio.create_task(collector.start()))

    bus.publish("SystemStarted", {
        "message": "Agent system started successfully"
    })

    while running:
        await asyncio.sleep(1)

    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())