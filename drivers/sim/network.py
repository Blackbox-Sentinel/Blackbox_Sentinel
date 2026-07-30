"""
Simulated network driver.

Stands in for real inline traffic capture. Returns fake packets instead
of reading from a real network interface.
"""

import random
import time


class Network:
    def __init__(self):
        self.connected = True

    def capture_packet(self):
        return {
            "timestamp": time.time(),
            "src": f"192.168.1.{random.randint(2, 254)}",
            "dst": f"192.168.1.{random.randint(2, 254)}",
            "size": random.randint(64, 1500),
        }

    def is_link_up(self):
        return self.connected

    def disconnect(self):
        self.connected = False
        print("[SIM][NET] Link disconnected (simulated)")
