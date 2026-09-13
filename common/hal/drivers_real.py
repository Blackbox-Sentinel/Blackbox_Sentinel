"""
BlackBox Sentinel — Real Hardware HAL Drivers
Pi 4 interfaces with ESP32 Heltec V3 via UART5 (GPIO 12/13).
ESP32 controls the physical relay (pins 4/5) and tamper monitoring.
"""

import time
import json
import os
from typing import Callable, Optional, Dict, Any
from .hal_base import RelayInterface, TamperInterface, LEDInterface, CellularInterface, MeshInterface


def _first_present(payload: Dict[str, Any], *keys: str, default: Any) -> Any:
    """Return the first key present in payload with a non-None value."""
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return default


# ── Safe GPIO & Serial Imports ────────────────────────────────────────────────
try:
    from gpiozero import Button
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


# ── ESP32 UART5 Bridge Singleton ─────────────────────────────────────────────
# Pi UART5: GPIO 12 = UART5 TXD, GPIO 13 = UART5 RXD  (Board pins 32/33)
# ESP32 Heltec V3: PI_RX_PIN = 19 (receives from Pi TX), PI_TX_PIN = 20
ESP32_PORT = "/dev/ttyAMA5"
ESP32_BAUD = 115200
_esp32_serial = None  # module-level singleton


def get_esp32_serial():
    """Return a cached shared serial connection to the ESP32 over UART5."""
    global _esp32_serial
    if _esp32_serial is not None:
        return _esp32_serial
    if not SERIAL_AVAILABLE:
        print("[HAL-REAL] ⚠️ pyserial not installed")
        return None
    if not os.path.exists(ESP32_PORT):
        print(f"[HAL-REAL] ⚠️ ESP32 port {ESP32_PORT} not found — is uart5 dtoverlay active?")
        return None
    try:
        _esp32_serial = serial.Serial(ESP32_PORT, baudrate=ESP32_BAUD, timeout=2)
        print(f"[HAL-REAL] 📡 ESP32 UART bridge active on {ESP32_PORT} @ {ESP32_BAUD} baud (GPIO12 TX / GPIO13 RX)")
    except Exception as e:
        print(f"[HAL-REAL] ⚠️ Failed to open ESP32 port: {e}")
        _esp32_serial = None
    return _esp32_serial


def send_receipt_to_esp32(receipt: Dict[str, Any]) -> bool:
    """Serialize and send a signed containment receipt to the ESP32 over UART5.
    
    The ESP32 Heltec firmware (blackbox_sentinel.ino) reads from Serial2 and
    expects a JSON object with 'signature' and 'payload' fields. It verifies
    the Ed25519 signature and only triggers the relay if valid.
    """
    ser = get_esp32_serial()
    if not ser:
        print("[HAL-REAL] ⚠️ Cannot send receipt: ESP32 serial not available")
        return False
    try:
        line = json.dumps(receipt, separators=(',', ':')) + "\n"
        ser.write(line.encode("utf-8"))
        ser.flush()
        print(f"[HAL-REAL] 📤 Sent signed receipt to ESP32 ({len(line)} bytes) — watch OLED for confirmation")
        return True
    except Exception as e:
        print(f"[HAL-REAL] ⚠️ Failed to send receipt: {e}")
        return False


# ── Relay Interface ───────────────────────────────────────────────────────────

class RealRelay(RelayInterface):
    """ESP32 Co-processor Relay via UART5 (GPIO12 TX/GPIO13 RX -> ESP32 GPIO19/20).
    
    The physical relay (RELAY1_PIN=4, RELAY2_PIN=5 on Heltec) is controlled
    by the ESP32. The Pi sends a signed Ed25519 JSON receipt; ESP32 validates
    and actuates the relay. The OLED on the Heltec shows the state change.
    """

    def __init__(self):
        self.state = "ENGAGED"
        self._last_receipt: Optional[Dict[str, Any]] = None
        get_esp32_serial()  # open port early so errors surface at startup
        print("[HAL-REAL] 🔌 ESP32 Relay bridge initialized (UART5 /dev/ttyAMA5)")

    def set_receipt(self, receipt: Dict[str, Any]) -> None:
        """Store the signed containment receipt to send when isolate() is called."""
        self._last_receipt = receipt

    def isolate(self) -> bool:
        self.state = "ISOLATED"
        if self._last_receipt:
            ok = send_receipt_to_esp32(self._last_receipt)
            print(f"[HAL-REAL] ⚡ [RELAY ISOLATE] Sent signed receipt to ESP32 -> relay CUT (ok={ok})")
            print("[HAL-REAL]    Watch the Heltec OLED: should show '!! ISOLATED !!'")
        else:
            print("[HAL-REAL] ⚠️  isolate() called but no receipt set — ESP32 will reject unsigned command")
        return True

    def engage(self) -> bool:
        self.state = "ENGAGED"
        # Physical restore is done by pressing the PRG button on the Heltec ESP32
        # (see loop() -> digitalRead(PRG_BUTTON_PIN) == LOW in the firmware)
        print("[HAL-REAL] ✅ [RELAY ENGAGE] State tracked locally — press ESP32 PRG button to physically restore relay")
        return True

    def get_state(self) -> str:
        return self.state

    def cleanup(self) -> None:
        global _esp32_serial
        if _esp32_serial:
            _esp32_serial.close()
            _esp32_serial = None


# ── Tamper Interface ──────────────────────────────────────────────────────────

class RealTamper(TamperInterface):
    """Anti-Tamper monitoring via ESP32 limit switch (ESP32 GPIO 14).
    
    The ESP32 firmware detects tamper via digitalRead(LIMIT_SWITCH_PIN) == HIGH
    and calls triggerIsolate("CHASSIS TAMPER") autonomously. On the Pi side,
    we monitor GPIO 27 as an additional signal if wired.
    """

    TAMPER_PINS = [27, 22]

    def __init__(self, on_tamper_callback: Optional[Callable[[], None]] = None):
        self.on_tamper = on_tamper_callback
        self.buttons = []
        self._tampered = False

        if GPIO_AVAILABLE:
            for pin in self.TAMPER_PINS:
                try:
                    btn = Button(pin, pull_up=True, bounce_time=0.1)
                    btn.when_pressed = self._handle_hardware_tamper
                    self.buttons.append(btn)
                except Exception as e:
                    print(f"[HAL-REAL] Warning: tamper pin {pin} init error: {e}")
            print(f"[HAL-REAL] 🛡️ Anti-tamper monitoring active on BCM Pins {self.TAMPER_PINS}")
        else:
            print("[HAL-REAL] ⚠️ gpiozero not available — tamper detection disabled on Pi side")

    def _handle_hardware_tamper(self, btn=None):
        if not self._tampered:
            self._tampered = True
            pin = btn.pin.number if btn else "UNKNOWN"
            print(f"\n[HAL-REAL] 🚨 [TAMPER DETECTED] Physical breach on GPIO {pin}!")
            if self.on_tamper:
                self.on_tamper()

    def is_tampered(self) -> bool:
        return self._tampered

    def simulate_tamper(self) -> None:
        self._handle_hardware_tamper()

    def cleanup(self) -> None:
        for b in self.buttons:
            b.close()


# ── LED Interface ─────────────────────────────────────────────────────────────

class RealLED(LEDInterface):
    """Status LED — delegated to ESP32 (PIN_LED_ARMED=2, PIN_LED_ALERT=4).
    
    The LED is physically on the ESP32. We track state locally only.
    """

    def __init__(self):
        self._state = "off"
        print("[HAL-REAL] 💡 LED state tracking active (physical LED on ESP32)")

    def solid_on(self) -> None:
        self._state = "on"

    def blink(self, interval: float = 0.2) -> None:
        self._state = "blink"

    def off(self) -> None:
        self._state = "off"

    def cleanup(self) -> None:
        self._state = "off"


# ── Cellular Interface ────────────────────────────────────────────────────────

class RealCellular(CellularInterface):
    """SIM800L GSM — controlled by ESP32 (Serial1 on ESP32 GPIO 47/48).
    
    The ESP32 sends SMS autonomously on isolation. From the Pi side this is
    a no-op since the SMS path runs entirely on the ESP32.
    """

    def __init__(self):
        print("[HAL-REAL] 📱 Cellular: SMS handled by ESP32 SIM800L (GPIO47/48)")

    def send_sms(self, phone_number: str, message: str) -> bool:
        # ESP32 sends SMS autonomously when triggerIsolate() is called
        print(f"[HAL-REAL] 📱 SMS to {phone_number} will be sent by ESP32 on relay trigger")
        return True

    def is_ready(self) -> bool:
        return True

    def cleanup(self) -> None:
        pass


# ── Mesh Interface ────────────────────────────────────────────────────────────

class RealMesh(MeshInterface):
    """ESP32 UART bridge via Pi UART5 on GPIO 12/13 (/dev/ttyAMA5)."""

    def __init__(self, port: str = "/dev/ttyAMA5", baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser = get_esp32_serial()  # reuse the shared singleton
        self.callbacks = []
        if self.ser:
            print(f"[HAL-REAL] 📡 ESP32 Mesh/C2 link active on {port} (shared UART5 singleton)")

    def broadcast_threat(self, threat_payload: Dict[str, Any]) -> bool:
        if not self.ser:
            return False
        try:
            threat_type = str(_first_present(
                threat_payload, "threat_type", "threat", "label", default="UNKNOWN"
            )).replace(":", "_").replace("\n", "_").replace("\r", "_")
            score = float(_first_present(
                threat_payload, "threat_score", "score", "anomaly_score", default=0.0
            ))
            port = int(_first_present(
                threat_payload, "victim_port", "port", "dst_port", default=0
            ))
            line = f"GOSSIP:{threat_type}:{score}:{port}\n"
            self.ser.write(line.encode("utf-8"))
            return True
        except Exception as e:
            print(f"[HAL-REAL] Mesh write error: {e}")
            return False

    def register_peer_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.callbacks.append(callback)

    def cleanup(self) -> None:
        pass  # shared serial closed by RealRelay.cleanup()
