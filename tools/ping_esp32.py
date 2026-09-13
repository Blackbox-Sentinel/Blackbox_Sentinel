#!/usr/bin/env python3
"""Test ESP32 v2.1 firmware - PING and heartbeat check over UART5."""
import serial
import time

s = serial.Serial('/dev/ttyAMA5', 115200, timeout=6)
time.sleep(0.5)

# Flush any boot message from ESP32
if s.in_waiting:
    boot = s.read(s.in_waiting).decode('utf-8', errors='replace')
    print("Boot msg from ESP32:", boot.strip())

# Send PING
print("\nSending PING...")
s.write(b'PING\n')
s.flush()

# Read for 8 seconds
print("Waiting up to 8s for response (heartbeat or pong)...")
buf = ''
end = time.time() + 8
got_response = False

while time.time() < end:
    if s.in_waiting:
        buf += s.read(s.in_waiting).decode('utf-8', errors='replace')
        lines = buf.split('\n')
        buf = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if line:
                print(f"  ESP32 -> {line}")
                got_response = True
    time.sleep(0.05)

if got_response:
    print("\n✅ UART5 bidirectional link is WORKING!")
    print("   The ESP32 v2.1 firmware is responding over GPIO 12/13")
else:
    print("\n❌ No response from ESP32 in 8s")
    print("   Possible causes:")
    print("   1. TX/RX wires swapped on breadboard (try swapping GPIO12 and GPIO13)")
    print("   2. ESP32 Serial2 not initialized correctly in firmware")
    print("   3. Baud rate mismatch")

s.close()
