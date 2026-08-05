"""
BlackBox Sentinel — HAL Factory
Instantiates and configures either Physical Hardware drivers or Simulation drivers
based on environment variables or automatic platform detection.
"""

import os
from typing import Callable, Optional
from .hal_base import SentinelHAL
from .drivers_sim import SimRelay, SimTamper, SimLED, SimCellular, SimMesh


def is_raspberry_pi() -> bool:
    """Detect if running on physical Raspberry Pi hardware."""
    try:
        if os.path.exists("/proc/device-tree/model"):
            with open("/proc/device-tree/model", "r", errors="ignore") as f:
                model = f.read().lower()
                if "raspberry pi" in model:
                    return True
    except Exception:
        pass
    return False


def get_hal(
    mode: Optional[str] = None,
    on_tamper_callback: Optional[Callable[[], None]] = None,
    on_relay_change: Optional[Callable[[str], None]] = None,
    node_id: str = "AEDN_NODE_01",
) -> SentinelHAL:
    """
    Factory method to retrieve Sentinel Hardware Abstraction Layer.
    
    Args:
        mode: Explicit 'real' or 'sim'. If None, reads from SENTINEL_HARDWARE env var.
        on_tamper_callback: Callback triggered when anti-tamper switch trips.
        on_relay_change: Callback triggered when relay state toggles.
        node_id: Unique identifier for ESP-NOW mesh networking.
        
    Returns:
        SentinelHAL container with configured driver instances.
    """
    if mode is None:
        mode = os.getenv("SENTINEL_HARDWARE", os.getenv("HARDWARE", "auto")).lower()

    if mode == "auto":
        mode = "real" if is_raspberry_pi() else "sim"

    print(f"[HAL] Initializing Hardware Abstraction Layer in mode: [{mode.upper()}]")

    if mode == "real":
        try:
            from .drivers_real import RealRelay, RealTamper, RealLED, RealCellular, RealMesh
            
            relay = RealRelay()
            tamper = RealTamper(on_tamper_callback=on_tamper_callback)
            led = RealLED()
            cellular = RealCellular()
            mesh = RealMesh()
            
            return SentinelHAL("real", relay, tamper, led, cellular, mesh)
        except Exception as e:
            print(f"[HAL] ⚠️ Failed to initialize Real Hardware ({e}). Falling back to SIMULATION.")
            mode = "sim"

    # Simulation fallback
    relay = SimRelay(on_state_change=on_relay_change)
    tamper = SimTamper(on_tamper_callback=on_tamper_callback)
    led = SimLED()
    cellular = SimCellular()
    mesh = SimMesh(node_id=node_id)

    return SentinelHAL("sim", relay, tamper, led, cellular, mesh)
