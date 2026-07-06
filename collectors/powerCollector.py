import asyncio
import os

from core.collector import Collector

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

    def read_ac(self):
        path = self.ac_file_path
        try:
            with open(path) as f:
                return f.read().strip() == "1"
        except FileNotFoundError:
            return None

    def read_battery(self):
        path = self.power_file_path
        try:
            with open(path) as f:
                return int(f.read().strip())
        except FileNotFoundError:
            return None

    async def start(self):
        try:
            # ensure running flag is set when starting
            self.running = True
            while self.running:
                ac = self.read_ac()
                battery = self.read_battery()

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

                await asyncio.sleep(2)
        except Exception as e:
            print(f"Error in PowerCollector: {e}")

    def stop(self):
        self.running = False