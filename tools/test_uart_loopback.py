#!/usr/bin/env python3
"""
Pi UART5 loopback test - helps diagnose if Pi TX is working.
Run while GPIO12 and GPIO13 are DISCONNECTED from ESP32.
Temporarily jumper GPIO12 (Pin 32) to GPIO13 (Pin 33) for loopback.

If loopback works: Pi UART is fine, problem is the wiring to ESP32.
If loopback fails: Pi UART itself has an issue.
"""
import serial
import time

PORT = "/dev/ttyAMA5"
BAUD = 115200

print(f"UART5 Loopback Test on {PORT}")
print("Make sure GPIO12 (Pin 32) is jumpered to GPIO13 (Pin 33)")
print()

ser = serial.Serial(PORT, BAUD, timeout=2)
time.sleep(0.5)

test_msg = b"SENTINEL_LOOPBACK_TEST_12345\n"
print(f"Sending: {test_msg}")
ser.write(test_msg)
time.sleep(0.5)

resp = ser.read(len(test_msg) + 10)
print(f"Received: {resp}")

if b"SENTINEL_LOOPBACK" in resp:
    print("\n✅ LOOPBACK PASS - Pi UART5 TX/RX are working correctly!")
    print("   Problem is with the wiring to ESP32 (check TX/RX swap)")
else:
    print("\n❌ LOOPBACK FAIL - Pi UART5 is not working")
    print("   Check: is uart5 dtoverlay active? Is /dev/ttyAMA5 the right device?")

ser.close()
