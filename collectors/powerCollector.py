import asyncio
import os

from core.collector import Collector

POLL_INTERVAL_SECONDS = 2

class PowerCollector(Collector):
    def __init__(self, bus):
        super().__init__(bus)

        self.last_ac_state = None
        self.last_battery = None

        self.power_file_path = os.getenv("POWER_FILE_PATH") or "/sys/class/power_supply/BAT1/capacity"  # Default path
        self.ac_file_path = os.getenv("AC_FILE_PATH") or "/sys/class/power_supply/ACAD/online"  # Default path

        self.state = {
            "battery": None,
            "ac": None
        }

    def health_timeout(self):
        # Ten missed polls means the loop is wedged, not just a slow read.
        return POLL_INTERVAL_SECONDS * 10

    def read_ac(self):
        path = self.ac_file_path
        try:
            with open(path) as f:
                return f.read().strip() == "1"
        except OSError:
            return None

    def read_battery(self):
        path = self.power_file_path
        try:
            with open(path) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            # Sysfs occasionally hands back a short or empty read; treat it as
            # "no reading this tick" rather than letting it kill the collector.
            return None

    def seed(self):
        """Establish the baseline without announcing it.

        PowerChanged/BatteryChanged mean "this moved". The first reading of a
        fresh process is not a move, it is just us finding out where things
        stand - publishing it made every restart look like someone had touched
        the charger.
        """
        self.last_ac_state = self.read_ac()
        self.last_battery = self.read_battery()

        self.state["ac"] = self.last_ac_state
        self.state["battery"] = self.last_battery

        # StateUpdated still goes out: /battery and /status read from the store.
        self.bus.publish("StateUpdated", self.state.copy())

    def poll(self):
        ac = self.read_ac()
        battery = self.read_battery()

        # A failed read is not a state change - hold the last known value so a
        # transient sysfs hiccup does not flap the state store or fire events.
        if ac is None and self.last_ac_state is not None:
            ac = self.last_ac_state

        if battery is None and self.last_battery is not None:
            battery = self.last_battery

        state_changed = False

        # Update local state first
        if ac != self.last_ac_state:
            self.state["ac"] = ac
            state_changed = True

        if battery != self.last_battery:
            self.state["battery"] = battery
            state_changed = True

        # Publish the new state once
        if state_changed:
            self.bus.publish("StateUpdated", self.state.copy())

        # Now publish specific events
        if ac != self.last_ac_state:
            self.bus.publish("PowerChanged", {
                "connected": ac,
                "message": "Charger plugged in" if ac else "Charger unplugged"
            })
            self.last_ac_state = ac

        if battery != self.last_battery:
            self.bus.publish("BatteryChanged", {
                "value": battery
            })
            self.last_battery = battery

    async def start(self):
        # ensure running flag is set when starting
        self.running = True

        self.seed()

        while self.running:
            self.mark_healthy()

            try:
                self.poll()
            except Exception as e:
                # Scoped to one tick: a single bad read used to escape the loop
                # and kill power monitoring for the rest of the process's life.
                print(f"Error in PowerCollector: {e}")

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    def stop(self):
        self.running = False
