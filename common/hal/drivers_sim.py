"""
BlackBox Sentinel — Simulation HAL Drivers
Provides fully functional software mocks for all physical hardware components.
"""

import sys
import time
import os
import json
import socket
import threading
from typing import Callable, Optional, Dict, Any
from .hal_base import RelayInterface, TamperInterface, LEDInterface, CellularInterface, MeshInterface

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class SimRelay(RelayInterface):
    """Simulated 5V Mechanical Isolation Relay."""

    def __init__(self, on_state_change: Optional[Callable[[str], None]] = None):
        self.state = "ENGAGED"
        self.on_state_change = on_state_change
        print("[HAL-SIM] [RELAY] Relay initialized in ENGAGED state (data line connected)")

    def isolate(self) -> bool:
        self.state = "ISOLATED"
        print("[HAL-SIM] [RELAY FIRED] Mechanical data line is now CUT / ISOLATED")
        if self.on_state_change:
            self.on_state_change(self.state)
        return True

    def engage(self) -> bool:
        self.state = "ENGAGED"
        print("[HAL-SIM] [RELAY ENGAGED] Mechanical data line is now RESTORED")
        if self.on_state_change:
            self.on_state_change(self.state)
        return True

    def get_state(self) -> str:
        return self.state

    def cleanup(self) -> None:
        self.state = "ENGAGED"
        print("[HAL-SIM] Relay cleaned up.")


class SimTamper(TamperInterface):
    """Simulated Enclosure Breach & Anti-Tamper Sensor."""

    def __init__(self, on_tamper_callback: Optional[Callable[[], None]] = None):
        self._tampered = False
        self.on_tamper = on_tamper_callback
        print("[HAL-SIM] [TAMPER] Monitor active (Grid continuous)")

    def is_tampered(self) -> bool:
        return self._tampered

    def simulate_tamper(self) -> None:
        if not self._tampered:
            self._tampered = True
            print("\n[HAL-SIM] [TAMPER ALERT] Enclosure breach detected! Triggering zeroization...")
            if self.on_tamper:
                self.on_tamper()

    def cleanup(self) -> None:
        self._tampered = False


class SimLED(LEDInterface):
    """Simulated Status LED."""

    def __init__(self):
        self.state = "OFF"
        print("[HAL-SIM] [LED] Status LED initialized (OFF)")

    def solid_on(self) -> None:
        self.state = "SOLID_ON"
        print("[HAL-SIM] [LED] [SOLID GREEN] — System Armed & Monitoring")

    def blink(self, interval: float = 0.2) -> None:
        self.state = f"BLINKING_{interval}s"
        print(f"[HAL-SIM] [LED] [RAPID FLASHING RED ({interval}s)] — System in ALERT / LOCKDOWN")

    def off(self) -> None:
        self.state = "OFF"
        print("[HAL-SIM] [LED] [OFF] — System Calibrating / Idle")

    def cleanup(self) -> None:
        self.state = "OFF"


class SimCellular(CellularInterface):
    """Simulated SIM800L GSM Cellular Modem."""

    def __init__(self, alert_log_path: Optional[str] = None):
        self.alert_log_path = alert_log_path or os.path.join(
            os.path.dirname(__file__), "..", "..", "m3-ml-ledger", "data", "oob_sms_alerts.log"
        )
        os.makedirs(os.path.dirname(self.alert_log_path), exist_ok=True)
        print("[HAL-SIM] [CELLULAR] SIM800L Modem: Registered to SIMULATED-2G-GSM Network (RSSI: 24/31)")

    def send_sms(self, phone_number: str, message: str) -> bool:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        alert_entry = f"[{timestamp}] SMS to {phone_number} -> {message}\n"
        
        print(f"\n[HAL-SIM] [CELLULAR OOB SMS SENT] Destination: {phone_number}")
        print(f"  Message: \"{message}\"")
        
        try:
            with open(self.alert_log_path, "a", encoding="utf-8") as f:
                f.write(alert_entry)
        except Exception as e:
            print(f"[HAL-SIM] Error logging SMS: {e}")
        return True

    def is_ready(self) -> bool:
        return True

    def cleanup(self) -> None:
        pass


class SimMesh(MeshInterface):
    """
    Simulated ESP-NOW Mesh Radio.
    Uses local UDP loopback broadcasting (port 39999) to gossip threat alerts
    between simulated node instances.
    """

    def __init__(self, node_id: str = "NODE_01", mesh_port: int = 39999):
        self.node_id = node_id
        self.mesh_port = mesh_port
        self.peer_callbacks = []
        self.running = True
        
        # Setup UDP listener for peer mesh messages
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("127.0.0.1", self.mesh_port))
            self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listener_thread.start()
            print(f"[HAL-SIM] [MESH] ESP-NOW Radio: Node '{self.node_id}' listening on UDP loopback :{self.mesh_port}")
        except Exception as e:
            print(f"[HAL-SIM] Mesh loopback binding note: {e}")
            self.sock = None

    def broadcast_threat(self, threat_payload: Dict[str, Any]) -> bool:
        payload = {
            "origin_node": self.node_id,
            "timestamp": time.time(),
            "type": "ESP_NOW_CONTAINMENT_BROADCAST",
            "data": threat_payload
        }
        msg_bytes = json.dumps(payload).encode("utf-8")
        
        print(f"[HAL-SIM] [ESP-NOW MESH BROADCAST] Gossiping threat profile to peer rack nodes...")
        print(f"  Payload: {threat_payload}")
        
        if self.sock:
            try:
                self.sock.sendto(msg_bytes, ("127.0.0.1", self.mesh_port))
            except Exception as e:
                print(f"[HAL-SIM] Mesh broadcast error: {e}")
        return True

    def register_peer_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.peer_callbacks.append(callback)

    def _listen_loop(self):
        while self.running and self.sock:
            try:
                data, addr = self.sock.recvfrom(4096)
                msg = json.loads(data.decode("utf-8"))
                if msg.get("origin_node") != self.node_id:
                    print(f"\n[HAL-SIM] [ESP-NOW MESH RECEIVED] Peer Threat Alert from {msg.get('origin_node')}!")
                    for cb in self.peer_callbacks:
                        cb(msg.get("data", {}))
            except Exception:
                pass

    def cleanup(self) -> None:
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
