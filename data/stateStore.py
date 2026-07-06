class StateStore:
    def __init__(self, bus):
        self.bus = bus
        self.state = {}

        self.bus.subscribe("StateUpdated", self.update_state)

    def update_state(self, context):
        self.state.update(context)

    def get(self, key):
        return self.state.get(key)