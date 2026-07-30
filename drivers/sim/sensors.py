"""
Simulated sensors driver.

Stands in for real onboard sensors (temperature, etc). Returns fixed
or lightly randomized fake values instead of reading real hardware.
"""

import random


class Sensors:
    def read_temperature(self):
        return round(28 + random.uniform(-1, 1), 1)

    def read_all(self):
        return {
            "temperature": self.read_temperature(),
        }
