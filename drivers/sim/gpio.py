"""
Simulated GPIO driver.

Stands in for real Raspberry Pi GPIO control so the project can run
on a laptop with no hardware attached. Nothing here talks to real pins.
"""


class GPIO:
    def __init__(self):
        self.pin_states = {}

    def setup(self, pin, mode):
        self.pin_states[pin] = 0
        print(f"[SIM][GPIO] Pin {pin} configured as {mode}")

    def output(self, pin, value):
        self.pin_states[pin] = value
        print(f"[SIM][GPIO] Pin {pin} set to {value}")

    def input(self, pin):
        return self.pin_states.get(pin, 0)

    def cut_line(self):
        print("[SIM][GPIO] Data line cut (simulated)")

    def cleanup(self):
        print("[SIM][GPIO] Cleanup complete")
