"""
BlackBox Sentinel — M1 Hardware: Relay & Tamper Controller
GPIO-driven relay isolation + anti-tamper switch monitoring.
Runs on the Raspberry Pi Zero 2 W.

Author: M1 Hardware Engineer
Branch: m1-dev

Pin Assignments (BCM numbering):
    GPIO 17 → Relay module IN (active-high = line CUT)
    GPIO 27 → Tamper switch 1 (lid, pull-up, active-low)
    GPIO 22 → Tamper switch 2 (side panel, pull-up, active-low)
    GPIO 23 → Status LED (armed = solid, alert = blink)
"""

import time
import threading

# ─── Try to import GPIO (fails gracefully on non-Pi systems) ──
try:
    from gpiozero import OutputDevice, Button, LED
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("[HW] gpiozero not available — running in simulation mode")


class RelayController:
    """
    Controls the 5V signal relay for physical data-line isolation.
    
    States:
        - ENGAGED: relay off, data line connected (normal)
        - ISOLATED: relay on, data line physically cut (lockdown)
    """
    
    RELAY_PIN = 17  # BCM pin
    
    def __init__(self):
        self.is_isolated = False
        if GPIO_AVAILABLE:
            self.relay = OutputDevice(self.RELAY_PIN, active_high=True, initial_value=False)
            print(f"[RELAY] Initialized on GPIO {self.RELAY_PIN} — ENGAGED (line connected)")
        else:
            self.relay = None
            print("[RELAY] Simulation mode — no physical relay")
    
    def isolate(self):
        """Fire the relay — physically cut the data line."""
        self.is_isolated = True
        if self.relay:
            self.relay.on()
        print("[RELAY] ⚡ ISOLATED — data line CUT")
        return True
    
    def engage(self):
        """Re-engage the relay — restore the data line."""
        self.is_isolated = False
        if self.relay:
            self.relay.off()
        print("[RELAY] ✅ ENGAGED — data line RESTORED")
        return True
    
    def get_state(self) -> str:
        """Return current relay state."""
        return "ISOLATED" if self.is_isolated else "ENGAGED"
    
    def cleanup(self):
        """Release GPIO resources."""
        if self.relay:
            self.relay.close()


class TamperMonitor:
    """
    Monitors anti-tamper microswitches on the enclosure.
    On tamper detection: triggers callback for key zeroization.
    
    Switches use internal pull-ups; pressing (enclosure opened) = LOW.
    """
    
    TAMPER_PINS = [27, 22]  # BCM pins for lid + side panel switches
    
    def __init__(self, on_tamper_callback=None):
        self.tampered = False
        self.on_tamper = on_tamper_callback or self._default_tamper_handler
        self.buttons = []
        
        if GPIO_AVAILABLE:
            for pin in self.TAMPER_PINS:
                btn = Button(pin, pull_up=True, bounce_time=0.1)
                btn.when_pressed = self._handle_tamper
                self.buttons.append(btn)
            print(f"[TAMPER] Monitoring {len(self.TAMPER_PINS)} switches")
        else:
            print("[TAMPER] Simulation mode — no physical switches")
    
    def _handle_tamper(self, button=None):
        """Called when any tamper switch is triggered."""
        if not self.tampered:
            self.tampered = True
            pin = button.pin.number if button else "SIM"
            print(f"[TAMPER] ⚠️  ENCLOSURE BREACH DETECTED on GPIO {pin}")
            self.on_tamper()
    
    def _default_tamper_handler(self):
        """Default handler — just logs. Override with zeroization callback."""
        print("[TAMPER] Default handler — implement key zeroization!")
    
    def simulate_tamper(self):
        """For testing on non-Pi systems."""
        print("[TAMPER] Simulating tamper event...")
        self._handle_tamper()
    
    def cleanup(self):
        """Release GPIO resources."""
        for btn in self.buttons:
            btn.close()


class StatusLED:
    """
    Status LED indicator.
    Solid = armed/normal, Blinking = alert, Off = calibrating.
    """
    
    LED_PIN = 23  # BCM pin
    
    def __init__(self):
        self._blink_thread = None
        self._blinking = False
        
        if GPIO_AVAILABLE:
            self.led = LED(self.LED_PIN)
            print(f"[LED] Initialized on GPIO {self.LED_PIN}")
        else:
            self.led = None
            print("[LED] Simulation mode")
    
    def solid_on(self):
        """Solid on — system armed."""
        self._stop_blink()
        if self.led:
            self.led.on()
        print("[LED] Solid ON (armed)")
    
    def blink(self, interval=0.3):
        """Fast blink — alert/anomaly detected."""
        self._stop_blink()
        self._blinking = True
        if self.led:
            self.led.blink(on_time=interval, off_time=interval)
        print(f"[LED] Blinking (alert) — {interval}s interval")
    
    def off(self):
        """Off — calibrating or idle."""
        self._stop_blink()
        if self.led:
            self.led.off()
        print("[LED] Off (calibrating)")
    
    def _stop_blink(self):
        self._blinking = False
    
    def cleanup(self):
        if self.led:
            self.led.close()


# ─── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    print("=== BlackBox Sentinel M1 — Hardware Controller Test ===\n")
    
    # Initialize hardware
    relay = RelayController()
    led = StatusLED()
    
    def on_tamper():
        print("[ZEROIZE] Wiping keys from tmpfs...")
        # In production: shutil.rmtree('/run/sentinel/keys', ignore_errors=True)
        relay.isolate()
        led.blink(0.1)
    
    tamper = TamperMonitor(on_tamper_callback=on_tamper)
    
    # Simulate lifecycle
    print("\n--- Calibration Mode ---")
    led.off()
    time.sleep(1)
    
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
    
    # Cleanup
    relay.cleanup()
    led.cleanup()
    tamper.cleanup()
    print("\n[DONE] Hardware test complete.")
