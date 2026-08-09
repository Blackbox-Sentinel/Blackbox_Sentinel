"""
BlackBox Sentinel — Simulation Traffic Generator
Generates realistic normal enterprise network traffic and reproducible attack vectors.
"""

import time
import random
import numpy as np
from typing import Dict, Any, Generator, Optional


class TrafficGenerator:
    """
    Simulates high-fidelity network traffic flows.
    """

    def __init__(self):
        self.prev_time = time.time()

    def generate_normal_packet(self) -> Dict[str, Any]:
        """
        Generate a single normal packet matching standard enterprise traffic.
        Mix of HTTP (80), HTTPS (443), DNS (53), NTP (123), SSH (22).
        """
        now = time.time()
        inter_arrival = max(0.001, np.random.exponential(scale=0.03))
        
        # Traffic mix distribution: 60% HTTPS, 25% HTTP, 10% DNS, 5% SSH
        r = random.random()
        if r < 0.60:
            dst_port = 443
            protocol = 6  # TCP
            size = int(np.random.normal(750, 200))
        elif r < 0.85:
            dst_port = 80
            protocol = 6  # TCP
            size = int(np.random.normal(500, 150))
        elif r < 0.95:
            dst_port = 53
            protocol = 17  # UDP
            size = int(np.random.normal(120, 30))
        else:
            dst_port = 22
            protocol = 6  # TCP
            size = int(np.random.normal(300, 80))

        size = max(64, min(1514, size))
        src_port = random.randint(1024, 65535)

        self.prev_time = now
        return {
            "packet_size": float(size),
            "inter_arrival": float(inter_arrival),
            "protocol": int(protocol),
            "src_port": int(src_port),
            "dst_port": int(dst_port),
            "is_synthetic_attack": False,
            "label": "NORMAL"
        }

    def generate_attack_packet(self, attack_type: str = "EXFILTRATION") -> Dict[str, Any]:
        """
        Generate an anomalous packet payload matching known attack vectors.
        
        Types:
            - EXFILTRATION: Jumbo anomalous UDP packet burst
            - SYN_FLOOD: Extremely high speed tiny SYN packets
            - PORT_SCAN: Rapid anomalous destination port sweeps
            - ZERO_DAY: Irregular protocol and extreme payload size
        """
        now = time.time()
        inter_arrival = max(0.0001, np.random.exponential(scale=0.001))

        if attack_type == "EXFILTRATION":
            packet = {
                "packet_size": float(np.random.uniform(9000, 15000)),  # Jumbo frame
                "inter_arrival": float(inter_arrival),
                "protocol": 17,  # UDP
                "src_port": 4444,
                "dst_port": 4444,
                "is_synthetic_attack": True,
                "label": "DATA_EXFILTRATION"
            }
        elif attack_type == "SYN_FLOOD":
            packet = {
                "packet_size": 44.0,  # Minimal TCP SYN size
                "inter_arrival": 0.00005,  # Microsecond burst
                "protocol": 6,  # TCP
                "src_port": random.randint(1024, 65535),
                "dst_port": 80,
                "is_synthetic_attack": True,
                "label": "SYN_FLOOD"
            }
        elif attack_type == "PORT_SCAN":
            packet = {
                "packet_size": 52.0,
                "inter_arrival": 0.001,
                "protocol": 6,
                "src_port": 51515,
                "dst_port": random.randint(1, 1024),
                "is_synthetic_attack": True,
                "label": "PORT_SCAN"
            }
        else:  # ZERO_DAY
            packet = {
                "packet_size": 25000.0,
                "inter_arrival": 12.5,
                "protocol": 254,  # Custom experimental protocol
                "src_port": 9999,
                "dst_port": 9999,
                "is_synthetic_attack": True,
                "label": "ZERO_DAY_EXPLOIT"
            }

        self.prev_time = now
        return packet

    def stream_traffic(
        self,
        count: int = 200,
        attack_interval: int = 50,
        attack_type: str = "EXFILTRATION"
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream a sequence of normal packets with periodic attacks injected."""
        for i in range(1, count + 1):
            if i % attack_interval == 0:
                yield self.generate_attack_packet(attack_type)
            else:
                yield self.generate_normal_packet()


if __name__ == "__main__":
    gen = TrafficGenerator()
    print("=== BlackBox Sentinel — Traffic Generator Test ===")
    print("\n--- Sample Normal Packets ---")
    for _ in range(3):
        print(" ", gen.generate_normal_packet())

    print("\n--- Sample Attack Packets ---")
    for atk in ["EXFILTRATION", "SYN_FLOOD", "PORT_SCAN", "ZERO_DAY"]:
        print(f"  [{atk}]", gen.generate_attack_packet(atk))
