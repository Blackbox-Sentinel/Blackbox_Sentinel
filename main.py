"""
BlackBox Sentinel entry point.

Phase 0: just prove the skeleton boots cleanly and heartbeats,
regardless of HARDWARE mode. No detection logic yet.
"""

import time

import config


def main():
    print("Starting BlackBox Sentinel...")

    if config.HARDWARE == "sim":
        print("Running in Simulation Mode...")
    else:
        print("Running in Real Hardware Mode...")

    try:
        while True:
            print("Heartbeat...")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down BlackBox Sentinel...")


if __name__ == "__main__":
    main()
