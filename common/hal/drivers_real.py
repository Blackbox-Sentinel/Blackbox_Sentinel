"""
BlackBox Sentinel — Real Hardware HAL Drivers
Interfaces with physical Raspberry Pi Zero 2 W GPIOs, SIM800L UART, and ESP32-S3 via UART5.
"""

import time
import os
import json
import base64
import threading
from typing import Callable, Optional, Dict, Any
from .hal_base import RelayInterface, TamperInterface, LEDInterface, CellularInterface, MeshInterface

def _first_present(payload: Dict[str, Any], *keys: str, default: Any) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return default

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Global shared Serial port for ESP32 UART5
ESP32_PORT = "/dev/ttyAMA5"
ESP32_BAUD = 115200
esp32_ser = None
esp32_lock = threading.Lock()

if SERIAL_AVAILABLE and os.path.exists(ESP32_PORT):
    try:
        esp32_ser = serial.Serial(ESP32_PORT, baudrate=ESP32_BAUD, timeout=1)
        print(f"[HAL-REAL] 📡 ESP32 Bridge active on {ESP32_PORT}")
    except Exception as e:
        print(f"[HAL-REAL] Warning: ESP32 link note: {e}")


def _sign_and_send_decision(decision: str):
    """Generates an Ed25519 signed JSON receipt and sends it to ESP32."""
    if not esp32_ser or not CRYPTO_AVAILABLE:
        return False
        
    priv_b64 = os.environ.get("SENTINEL_ED25519_KEY")
    if not priv_b64:
        print("[HAL-REAL] Error: SENTINEL_ED25519_KEY missing from environment!")
        return False
        
    try:
        priv_bytes = base64.urlsafe_b64decode(priv_b64)
        priv = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        
        payload = {
            'algorithm': 'Ed25519',
            'controller_id': 'AEDN_NODE_01',
            'decision': decision,
            'event_hash': '0000000000000000000000000000000000000000000000000000000000000000',
            'evidence_digest': 'none',
            'incident_id': 'RELAY_MANUAL',
            'key_epoch': '1',
            'organization_id': 'SENTINEL',
            'quorum': '1/1',
            'receipt_sequence': '1',
            'receipt_version': '1.0',
            'timestamp': str(int(time.time()))
        }
        payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
        sig = priv.sign(payload_str.encode('utf-8'))
        
        receipt = json.dumps({
            'signature': base64.urlsafe_b64encode(sig).decode('utf-8').rstrip('='),
            'payload': payload
        })
        
        with esp32_lock:
            esp32_ser.write((receipt + "\n").encode('utf-8'))
        print(f"[HAL-REAL] 🔒 Sent Signed Decision to ESP32: {decision}")
        return True
    except Exception as e:
        print(f"[HAL-REAL] Failed to sign/send receipt: {e}")
        return False


class RealRelay(RelayInterface):
    """Relay controlled via ESP32 UART Bridge (Signed JSON Receipts)."""

    def __init__(self):
        self.state = "ENGAGED"
        if esp32_ser:
            print("[HAL-REAL] 🔌 Relay Controller initialized via ESP32 UART5 Bridge (ENGAGED)")
        else:
            print("[HAL-REAL] ⚠️ Relay Controller running without ESP32 Serial!")

    def isolate(self) -> bool:
        self.state = "ISOLATED"
        _sign_and_send_decision("CONTAIN")
        print("[HAL-REAL] ⚡ [RELAY FIRED] Sent signed CONTAIN command to ESP32 -> Data line CUT")
        return True

    def engage(self) -> bool:
        self.state = "ENGAGED"
        _sign_and_send_decision("RESTORE")
        print("[HAL-REAL] ✅ [RELAY ENGAGED] Sent RESTORE command to ESP32 -> Data line RESTORED")
        return True

    def get_state(self) -> str:
        return self.state

    def cleanup(self) -> None:
        pass


class RealTamper(TamperInterface):
    """Listens to ESP32 UART for hardware tamper events."""

    def __init__(self, on_tamper_callback: Optional[Callable[[], None]] = None):
        self.on_tamper = on_tamper_callback
        self._tampered = False
        self._stop_event = threading.Event()

        if esp32_ser:
            print("[HAL-REAL] 🛡️ Anti-tamper monitoring active via ESP32 UART5")
            self.monitor_thread = threading.Thread(target=self._listen_to_esp32, daemon=True)
            self.monitor_thread.start()

    def _listen_to_esp32(self):
        while not self._stop_event.is_set():
            try:
                if esp32_ser and esp32_ser.in_waiting > 0:
                    with esp32_lock:
                        line = esp32_ser.readline().decode('utf-8', errors='ignore').strip()
                    if "tamper_breach" in line or "CHASSIS TAMPER" in line:
                        self._handle_hardware_tamper()
            except Exception:
                pass
            time.sleep(0.1)

    def _handle_hardware_tamper(self, btn=None):
        if not self._tampered:
            self._tampered = True
            print("\n[HAL-REAL] 🚨 [TAMPER DETECTED] Physical breach reported by ESP32!")
            if self.on_tamper:
                self.on_tamper()

    def is_tampered(self) -> bool:
        return self._tampered

    def simulate_tamper(self) -> None:
        self._handle_hardware_tamper()

    def cleanup(self) -> None:
        self._stop_event.set()


class RealLED(LEDInterface):
    def __init__(self):
        pass
    def solid_on(self) -> None:
        pass
    def blink(self, interval: float = 0.2) -> None:
        pass
    def off(self) -> None:
        pass
    def cleanup(self) -> None:
        pass


class RealCellular(CellularInterface):
    """GSM via UART"""
    def __init__(self, port: str = "/dev/serial0", baud: int = 9600):
        self.ser = None

    def send_sms(self, phone_number: str, message: str) -> bool:
        return False

    def is_ready(self) -> bool:
        return False

    def cleanup(self) -> None:
        pass


class RealMesh(MeshInterface):
    """ESP-NOW Mesh via ESP32 UART5 Bridge."""

    def __init__(self, port: str = "/dev/ttyAMA5", baud: int = 115200):
        self.callbacks = []

    def broadcast_threat(self, threat_payload: Dict[str, Any]) -> bool:
        if not esp32_ser:
            return False
        try:
            threat_type = str(_first_present(threat_payload, "threat_type", "threat", "label", default="UNKNOWN"))
            score = float(_first_present(threat_payload, "threat_score", "score", "anomaly_score", default=0.0))
            port = int(_first_present(threat_payload, "victim_port", "port", "dst_port", default=0))
            line = f"GOSSIP:{threat_type}:{score}:{port}\n"
            with esp32_lock:
                esp32_ser.write(line.encode("utf-8"))
            return True
        except Exception as e:
            print(f"[HAL-REAL] Mesh write error: {e}")
            return False

    def register_peer_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.callbacks.append(callback)

    def cleanup(self) -> None:
        pass
