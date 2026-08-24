"""
BlackBox Sentinel — M2 Systems: Packet Capture
Scapy-based network sniffer that saves captured packets to .pcap files.

Author: M2 Systems Engineer
Branch: m2-dev
"""

import argparse
import os
import sys
from datetime import datetime

from scapy.all import get_if_list, sniff, wrpcap
from scapy.consts import WINDOWS

# ─── Configuration ────────────────────────────────────────────
CAPTURE_COUNT = 1000        # Packets per capture file
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "m3-ml-ledger", "data")

_LOOPBACK_MARKERS = ("loopback", "lo0")
_LINK_LOCAL_PREFIXES = ("fe80", "169.254.")


def packet_callback(packet):
    """Process each captured packet."""
    print(f"[CAPTURE] {packet.summary()}")


def _resolve_interface_windows():
    """Auto-detect on Windows using get_windows_if_list()'s richer metadata.

    Imported lazily: scapy.arch.windows imports winreg at module level,
    which does not exist on non-Windows platforms.
    """
    from scapy.arch.windows import get_windows_if_list

    candidates = [
        iface for iface in get_windows_if_list()
        if iface.get("ips")
        and iface.get("type") != 24
        and "loopback" not in iface.get("description", "").lower()
        and any(
            not ip.startswith(_LINK_LOCAL_PREFIXES)
            for ip in iface["ips"]
        )
    ]

    if len(candidates) == 1:
        selected = candidates[0]["description"]
        print(f"[AUTO-DETECT] Selected interface: {selected}")
        return selected

    if not candidates:
        print("[FATAL] No non-loopback interface with a real IP could be auto-selected.")
    else:
        print("[FATAL] Multiple candidate interfaces found — cannot auto-select confidently.")
        # Known limitation: a VM host-only adapter (VirtualBox/VMware/Hyper-V)
        # with a real assigned IP will land here alongside the physical NIC —
        # there's no reliable way to distinguish "real NIC" from "VM adapter
        # with a real IP" from ip-presence data alone without guessing, so we
        # require an explicit --iface instead.
    print("Available interfaces (pass one via --iface):")
    for iface in get_windows_if_list():
        print(f"  {iface['description']}")
    sys.exit(1)


def _resolve_interface_posix():
    """Auto-detect on non-Windows platforms via get_if_list()'s friendly names."""
    candidates = [
        name for name in get_if_list()
        if not any(marker in name.lower() for marker in _LOOPBACK_MARKERS)
    ]

    if len(candidates) == 1:
        print(f"[AUTO-DETECT] Selected interface: {candidates[0]}")
        return candidates[0]

    all_ifaces = get_if_list()
    if not candidates:
        print("[FATAL] No non-loopback interface could be auto-selected.")
    else:
        print("[FATAL] Multiple candidate interfaces found — cannot auto-select confidently.")
    print("Available interfaces (pass one via --iface):")
    for name in all_ifaces:
        print(f"  {name}")
    sys.exit(1)


def resolve_interface(requested_iface):
    """Return the interface to capture on, or exit(1) with guidance."""
    if requested_iface:
        return requested_iface

    if WINDOWS:
        return _resolve_interface_windows()
    return _resolve_interface_posix()


def run_capture(iface):
    """Start packet capture and save to pcap file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"capture_{timestamp}.pcap")

    print(f"=== BlackBox Sentinel M2 — Packet Capture ===")
    print(f"Interface: {iface}")
    print(f"Output: {output_file}")
    print(f"Capturing {CAPTURE_COUNT} packets...\n")

    packets = sniff(
        iface=iface,
        count=CAPTURE_COUNT,
        prn=packet_callback
    )

    wrpcap(output_file, packets)
    print(f"\n[DONE] Saved {len(packets)} packets to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="BlackBox Sentinel M2 packet capture.")
    parser.add_argument("--iface", type=str, default=None, help="Network interface to capture on.")
    args = parser.parse_args()

    iface = resolve_interface(args.iface)
    run_capture(iface)


if __name__ == "__main__":
    main()
