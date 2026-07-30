"""
Central configuration.

HARDWARE controls which driver set gets loaded everywhere else in the
project. This is the only switch that should ever need to change to
move between simulation and real hardware.

Usage:
    HARDWARE=sim  python main.py   (default)
    HARDWARE=real python main.py
"""

import os

HARDWARE = os.environ.get("HARDWARE", "sim").lower()

if HARDWARE not in ("sim", "real"):
    raise ValueError(f"Invalid HARDWARE value: '{HARDWARE}'. Use 'sim' or 'real'.")

if HARDWARE == "sim":
    from drivers.sim.gpio import GPIO
    from drivers.sim.network import Network
    from drivers.sim.sms import SMS
    from drivers.sim.sensors import Sensors
else:
    from drivers.real.gpio import GPIO
    from drivers.real.network import Network
    from drivers.real.sms import SMS
    from drivers.real.sensors import Sensors
