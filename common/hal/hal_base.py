"""
BlackBox Sentinel — Hardware Abstraction Layer (HAL) Interfaces
Defines common abstract interfaces for both Physical and Simulated hardware.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any


class RelayInterface(ABC):
    """Controls physical data-line mechanical isolation relay."""

    @abstractmethod
    def isolate(self) -> bool:
        """Fire relay to physically sever network cable."""
        pass

    @abstractmethod
    def engage(self) -> bool:
        """Re-engage relay to restore physical network connection."""
        pass

    @abstractmethod
    def get_state(self) -> str:
        """Return 'ENGAGED' or 'ISOLATED'."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release underlying hardware resources."""
        pass


class TamperInterface(ABC):
    """Monitors enclosure physical security grid and triggers zeroization."""

    @abstractmethod
    def is_tampered(self) -> bool:
        """Check if tamper circuit has been tripped."""
        pass

    @abstractmethod
    def simulate_tamper(self) -> None:
        """Manually trigger a tamper interrupt (testing/simulation)."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release hardware pins / interrupts."""
        pass


class LEDInterface(ABC):
    """Drives multi-state status indicator LED."""

    @abstractmethod
    def solid_on(self) -> None:
        """Solid light (Armed / Normal operation)."""
        pass

    @abstractmethod
    def blink(self, interval: float = 0.2) -> None:
        """Rapid flash (Alert / Lockdown / Tamper)."""
        pass

    @abstractmethod
    def off(self) -> None:
        """Turn off (Calibrating / Idle)."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Release LED pin."""
        pass


class CellularInterface(ABC):
    """Out-of-Band (OOB) GSM/Cellular alerting via SIM800L."""

    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send urgent SMS alert over cellular backup channel."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if GSM modem is registered on network."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Close serial interface."""
        pass


class MeshInterface(ABC):
    """ESP-NOW Ad-hoc P2P mesh network for multi-node coordinated containment."""

    @abstractmethod
    def broadcast_threat(self, threat_payload: Dict[str, Any]) -> bool:
        """Broadcast attacker profile to neighboring rack nodes."""
        pass

    @abstractmethod
    def register_peer_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register listener for inbound threat gossip messages."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Close mesh radio resources."""
        pass


class SentinelHAL:
    """Unified Hardware Abstraction Container."""

    def __init__(
        self,
        mode: str,
        relay: RelayInterface,
        tamper: TamperInterface,
        led: LEDInterface,
        cellular: CellularInterface,
        mesh: MeshInterface,
    ):
        self.mode = mode
        self.relay = relay
        self.tamper = tamper
        self.led = led
        self.cellular = cellular
        self.mesh = mesh

    def cleanup(self):
        """Clean up all subsystems."""
        self.relay.cleanup()
        self.tamper.cleanup()
        self.led.cleanup()
        self.cellular.cleanup()
        self.mesh.cleanup()
