"""
BlackBox Sentinel — M2 Systems: Serial Bridge
Reads raw packet bytes from ESP32 over USB serial and writes to pcap.

Author: M2 Systems Engineer
Branch: m2-dev
"""

import serial
from datetime import datetime
import os

# ─── Configuration ────────────────────────────────────────────
SERIAL_PORT = "COM3"        # Windows: COM3, Linux: /dev/ttyUSB0
BAUD_RATE = 115200
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "m3-ml-ledger", "data")


def run_bridge():
    """Bridge ESP32 serial output to pcap-compatible log."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"serial_{timestamp}.log")
    
    print(f"=== BlackBox Sentinel M2 — Serial Bridge ===")
    print(f"Port: {SERIAL_PORT} @ {BAUD_RATE} baud")
    print(f"Output: {output_file}")
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print("Connected! Reading serial data...\n")
        
        with open(output_file, "w") as f:
            while True:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    print(f"[SERIAL] {line}")
                    f.write(f"{datetime.now().isoformat()} | {line}\n")
                    f.flush()
                    
    except serial.SerialException as e:
        print(f"[ERROR] Serial connection failed: {e}")
    except KeyboardInterrupt:
        print("\n[STOP] Bridge terminated by user.")


if __name__ == "__main__":
    run_bridge()
