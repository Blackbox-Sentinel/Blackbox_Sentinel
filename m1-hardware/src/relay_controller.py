"""
BlackBox Sentinel — M1 Hardware: Relay & Tamper Controller (Trusted Coprocessor)
Re-engineered for Patent Scope: The Raspberry Pi no longer drives the relay directly.
Instead, it communicates via Serial with the ESP32 "Trusted Controller" which 
acts as an independent hardware enclave for anti-tamper security.

Author: M1 Hardware Engineer
Branch: m1-dev-coprocessor
"""

import time
import threading
import serial

try:
    # Attempt to open the Serial port to the ESP32
    # This will be /dev/ttyUSB0 (if plugged via USB) or /dev/serial0 (if wired via UART)
    esp32_serial = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    SERIAL_AVAILABLE = True
except Exception as e:
    SERIAL_AVAILABLE = False
    print(f"[HW] Serial port not available ({e}) — running in simulation mode")


class RelayController:
    """
    Sends secure commands to the ESP32 to control the 5V signal relay.
    
    States:
        - ENGAGED: relay off, data line connected (normal)
        - ISOLATED: relay on, data line physically cut (lockdown)
    """
    
    def __init__(self):
        self.is_isolated = False
        if SERIAL_AVAILABLE:
            print("[RELAY] Initialized via ESP32 Serial — ENGAGED (line connected)")
        else:
            print("[RELAY] Simulation mode — no physical serial bridge")
    
    def isolate(self):
        """Send ISOLATE command to ESP32."""
        self.is_isolated = True
        if SERIAL_AVAILABLE:
            esp32_serial.write(b"CMD:ISOLATE\n")
        print("[RELAY] ⚡ ISOLATED — Command sent to ESP32 to CUT data line")
        return True
    
    def engage(self):
        """Send ENGAGE command to ESP32."""
        self.is_isolated = False
        if SERIAL_AVAILABLE:
            esp32_serial.write(b"CMD:ENGAGE\n")
        print("[RELAY] ✅ ENGAGED — Command sent to ESP32 to RESTORE data line")
        return True
    
    def get_state(self) -> str:
        """Return current relay state."""
        return "ISOLATED" if self.is_isolated else "ENGAGED"
    
    def cleanup(self):
        """No GPIO to clean up; Serial is handled globally."""
        pass


class TamperMonitor:
    """
    Listens to the ESP32 via Serial for hardware tamper events.
    If the ESP32 detects a breach, it sends "EVENT:TAMPER".
    """
    
    def __init__(self, on_tamper_callback=None):
        self.tampered = False
        self.on_tamper = on_tamper_callback or self._default_tamper_handler
        self._stop_event = threading.Event()
        
        if SERIAL_AVAILABLE:
            print("[TAMPER] Monitoring ESP32 for hardware breach events...")
            self.monitor_thread = threading.Thread(target=self._listen_to_esp32, daemon=True)
            self.monitor_thread.start()
        else:
            print("[TAMPER] Simulation mode — no physical switches")
            
    def _listen_to_esp32(self):
        """Background thread to read Serial incoming data."""
        while not self._stop_event.is_set():
            if esp32_serial.in_waiting > 0:
                try:
                    line = esp32_serial.readline().decode('utf-8').strip()
                    if line == "EVENT:TAMPER":
                        self._handle_tamper("ESP32_HARDWARE_SWITCH")
                except Exception:
                    pass
            time.sleep(0.1)
    
    def _handle_tamper(self, source="SIM"):
        """Called when a tamper event is received from the ESP32."""
        if not self.tampered:
            self.tampered = True
            print(f"[TAMPER] ⚠️  ENCLOSURE BREACH DETECTED via {source}")
            self.on_tamper()
    
    def _default_tamper_handler(self):
        """Default handler — just logs. Override with zeroization callback."""
        print("[TAMPER] Default handler — implement key zeroization!")
    
    def simulate_tamper(self):
        """For testing on non-Pi systems."""
        print("[TAMPER] Simulating tamper event...")
        self._handle_tamper()
    
    def cleanup(self):
        """Stop the background monitoring thread."""
        self._stop_event.set()


class StatusLED:
    """
    Sends LED blink commands to the ESP32 to control the status indicator.
    """
    
    def __init__(self):
        if SERIAL_AVAILABLE:
            print("[LED] Initialized via ESP32 Serial")
        else:
            print("[LED] Simulation mode")
    
    def solid_on(self):
        if SERIAL_AVAILABLE:
            esp32_serial.write(b"CMD:LED_ON\n")
        print("[LED] Solid ON (armed)")
    
    def blink(self, interval=0.3):
        if SERIAL_AVAILABLE:
            esp32_serial.write(b"CMD:LED_BLINK\n")
        print(f"[LED] Blinking (alert)")
    
    def off(self):
        if SERIAL_AVAILABLE:
            esp32_serial.write(b"CMD:LED_OFF\n")
        print("[LED] Off (calibrating)")
    
    def cleanup(self):
        pass


# ─── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    print("=== BlackBox Sentinel M1 — ESP32 Trusted Coprocessor Bridge ===\n")
    
    relay = RelayController()
    led = StatusLED()
    
    def on_tamper():
        print("[ZEROIZE] Wiping keys from memory (Triggered by ESP32!)")
        relay.isolate()
        led.blink()
    
    tamper = TamperMonitor(on_tamper_callback=on_tamper)
    
    print("\n--- Armed Mode ---")
    led.solid_on()
    time.sleep(1)
    
    print("\n--- Anomaly Detected ---")
    led.blink()
    relay.isolate()
    time.sleep(2)
    
    print("\n--- PIN Override ---")
    relay.engage()
    led.solid_on()
    time.sleep(1)
    
    print("\n--- Tamper Test ---")
    tamper.simulate_tamper()
    time.sleep(1)
    
    relay.cleanup()
    led.cleanup()
    tamper.cleanup()
    print("\n[DONE] Bridge test complete.")
