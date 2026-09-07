"""
BlackBox Sentinel — Real Hardware HAL Drivers
Interfaces with physical Raspberry Pi Zero 2 W GPIOs, SIM800L UART, and ESP32-S3.
"""

import time
import os
from typing import Callable, Optional, Dict, Any
from .hal_base import RelayInterface, TamperInterface, LEDInterface, CellularInterface, MeshInterface


def _first_present(payload: Dict[str, Any], *keys: str, default: Any) -> Any:
    """Return the first key present in payload with a non-None value.

    Real callers of RealMesh.broadcast_threat() don't agree on field names
    (sentinel_pipeline.py uses threat_score/source_node, run_simulation.py
    uses threat_type/victim_port, hw_simulator_server.py uses threat/score),
    unlike the sim HAL which forwards the dict opaquely. The ESP32's GOSSIP:
    format needs specific typed fields, so this picks by alias instead of a
    single fixed key.
    """
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return default


# ── Safe GPIO & Serial Imports ─────────────────────────────────────────────────
try:
    from gpiozero import OutputDevice, Button, LED
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class RealRelay(RelayInterface):
    """Real 5V Signal Relay via Raspberry Pi GPIO 17."""

    RELAY_PIN = 17  # BCM 17

    def __init__(self):
        if not GPIO_AVAILABLE:
            raise RuntimeError("gpiozero is required for RealRelay")
        self.device = OutputDevice(self.RELAY_PIN, active_high=True, initial_value=False)
        self.state = "ENGAGED"
        print(f"[HAL-REAL] 🔌 Physical Relay initialized on BCM GPIO {self.RELAY_PIN} (ENGAGED)")

    def isolate(self) -> bool:
        self.device.on()
        self.state = "ISOLATED"
        print(f"[HAL-REAL] ⚡ [RELAY FIRED] GPIO {self.RELAY_PIN} HIGH -> Data line physically CUT")
        return True

    def engage(self) -> bool:
        self.device.off()
        self.state = "ENGAGED"
        print(f"[HAL-REAL] ✅ [RELAY ENGAGED] GPIO {self.RELAY_PIN} LOW -> Data line RESTORED")
        return True

    def get_state(self) -> str:
        return self.state

    def cleanup(self) -> None:
        self.device.off()
        self.device.close()


class RealTamper(TamperInterface):
    """Real Anti-Tamper Grid & Microswitches on BCM GPIO 27 & 22."""

    TAMPER_PINS = [27, 22]

    def __init__(self, on_tamper_callback: Optional[Callable[[], None]] = None):
        if not GPIO_AVAILABLE:
            raise RuntimeError("gpiozero is required for RealTamper")
        self.on_tamper = on_tamper_callback
        self.buttons = []
        self._tampered = False

        for pin in self.TAMPER_PINS:
            btn = Button(pin, pull_up=True, bounce_time=0.1)
            btn.when_pressed = self._handle_hardware_tamper
            self.buttons.append(btn)
        print(f"[HAL-REAL] 🛡️ Anti-tamper monitoring active on BCM Pins {self.TAMPER_PINS}")

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


class RealLED(LEDInterface):
    """Real Status LED on BCM GPIO 23."""

    LED_PIN = 23

    def __init__(self):
        if not GPIO_AVAILABLE:
            raise RuntimeError("gpiozero is required for RealLED")
        self.device = LED(self.LED_PIN)
        print(f"[HAL-REAL] 💡 Status LED initialized on BCM GPIO {self.LED_PIN}")

    def solid_on(self) -> None:
        self.device.on()

    def blink(self, interval: float = 0.2) -> None:
        self.device.blink(on_time=interval, off_time=interval)

    def off(self) -> None:
        self.device.off()

    def cleanup(self) -> None:
        self.device.off()
        self.device.close()


class RealCellular(CellularInterface):
    """Real SIM800L GSM Breakout via Raspberry Pi UART (/dev/serial0)."""

    def __init__(self, port: str = "/dev/serial0", baud: int = 9600):
        self.port = port
        self.baud = baud
        self.ser = None
        if SERIAL_AVAILABLE and os.path.exists(port):
            try:
                self.ser = serial.Serial(port, baudrate=baud, timeout=3)
                self._send_cmd("AT")
                self._send_cmd("AT+CMGF=1")  # SMS text mode
                print(f"[HAL-REAL] 📱 SIM800L initialized on {port} @ {baud} baud")
            except Exception as e:
                print(f"[HAL-REAL] Warning: SIM800L init error: {e}")

    def _send_cmd(self, cmd: str) -> str:
        if not self.ser:
            return ""
        self.ser.write((cmd + "\r\n").encode("utf-8"))
        time.sleep(0.5)
        return self.ser.read(self.ser.in_waiting or 1).decode("utf-8", errors="ignore")

    def send_sms(self, phone_number: str, message: str) -> bool:
        if not self.ser:
            print(f"[HAL-REAL] Error: SIM800L serial port not available")
            return False
        try:
            print(f"[HAL-REAL] 📤 Sending cellular SMS to {phone_number}...")
            self.ser.write(f'AT+CMGS="{phone_number}"\r\n'.encode("utf-8"))
            time.sleep(0.5)
            self.ser.write(f"{message}\x1A".encode("utf-8"))  # Ctrl+Z to send
            time.sleep(3.0)
            return True
        except Exception as e:
            print(f"[HAL-REAL] Failed to send SMS: {e}")
            return False

    def is_ready(self) -> bool:
        return self.ser is not None

    def cleanup(self) -> None:
        if self.ser:
            self.ser.close()


class RealMesh(MeshInterface):
    """Real ESP-NOW Mesh link via ESP32-S3 USB Serial (/dev/ttyUSB0)."""

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200):
        self.port = port
        self.baud = baud
        self.ser = None
        self.callbacks = []
        if SERIAL_AVAILABLE and os.path.exists(port):
            try:
                self.ser = serial.Serial(port, baudrate=baud, timeout=1)
                print(f"[HAL-REAL] 📡 ESP32-S3 Mesh link active on {port}")
            except Exception as e:
                print(f"[HAL-REAL] Warning: ESP32 link note: {e}")

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
        if self.ser:
            self.ser.close()
