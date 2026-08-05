"""
BlackBox Sentinel — M2 Systems: Packet Capture
Scapy-based network sniffer that saves captured packets to .pcap files.

Author: M2 Systems Engineer
Branch: m2-dev
"""

from scapy.all import sniff, wrpcap
from datetime import datetime
import os

# ─── Configuration ────────────────────────────────────────────
CAPTURE_INTERFACE = "eth0"  # Change to your network interface
CAPTURE_COUNT = 1000        # Packets per capture file
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "m3-ml-ledger", "data")


def packet_callback(packet):
    """Process each captured packet."""
    print(f"[CAPTURE] {packet.summary()}")


def run_capture():
    """Start packet capture and save to pcap file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"capture_{timestamp}.pcap")
    
    print(f"=== BlackBox Sentinel M2 — Packet Capture ===")
    print(f"Interface: {CAPTURE_INTERFACE}")
    print(f"Output: {output_file}")
    print(f"Capturing {CAPTURE_COUNT} packets...\n")
    
    packets = sniff(
        iface=CAPTURE_INTERFACE,
        count=CAPTURE_COUNT,
        prn=packet_callback
    )
    
    wrpcap(output_file, packets)
    print(f"\n[DONE] Saved {len(packets)} packets to {output_file}")


if __name__ == "__main__":
    run_capture()
