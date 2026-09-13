#!/usr/bin/env python3
"""
BlackBox Sentinel - ESP32 UART Bridge Test
Sends a minimal JSON to the ESP32 over /dev/ttyAMA5 (GPIO 12/13)
and reads back whatever the ESP32 sends (heartbeat, rejection msg, etc.)
Run on the Pi: sudo python3 /tmp/test_esp32_uart.py
"""
import serial
import time
import json

PORT = "/dev/ttyAMA5"
BAUD = 115200

print(f"Opening {PORT} at {BAUD} baud...")
try:
    ser = serial.Serial(PORT, BAUD, timeout=3)
    print("Port opened OK")
except Exception as e:
    print(f"FAILED to open port: {e}")
    raise

# Flush any boot messages
time.sleep(1)
if ser.in_waiting:
    boot_data = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
    print(f"Boot data from ESP32:\n{boot_data}")

# Send a SET_PHONE command - simple non-JSON that ESP32 handles
# This will trigger "RAW COMMAND REJECTED. MUST BE SIGNED JSON." on ESP32
# proving the UART line is alive
print("\n--- Sending SET_PHONE test command ---")
ser.write(b"SET_PHONE:+919914551405\n")
time.sleep(1)

resp = ser.read(ser.in_waiting or 64).decode("utf-8", errors="replace")
print(f"ESP32 response: {resp!r}")

# Now send a deliberately malformed JSON to get a clear rejection response
print("\n--- Sending malformed JSON (should get REJECTED response) ---")
test_msg = json.dumps({"signature": "AAAA", "payload": {"decision": "CONTAIN"}})
ser.write((test_msg + "\n").encode("utf-8"))
time.sleep(2)

resp = ser.read(ser.in_waiting or 256).decode("utf-8", errors="replace")
print(f"ESP32 response: {resp!r}")

# Wait for heartbeat (ESP32 sends one every 5 seconds)
print("\n--- Waiting up to 10s for ESP32 heartbeat ---")
start = time.time()
buf = ""
while time.time() - start < 10:
    if ser.in_waiting:
        buf += ser.read(ser.in_waiting).decode("utf-8", errors="replace")
        if "\n" in buf:
            line, buf = buf.split("\n", 1)
            print(f"ESP32 heartbeat: {line.strip()}")
            break
    time.sleep(0.1)
else:
    print("No heartbeat received in 10s")
    print("Check: Is ESP32 powered on? Are GPIO 12/13 wired correctly?")

ser.close()
print("\nTest complete.")
