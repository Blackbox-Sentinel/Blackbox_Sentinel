from scapy.all import sniff, IP, TCP, UDP, ICMP
import csv
import os
from datetime import datetime
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "traffic.csv"

# 21 features matching the training data
header = [
    "timestamp", "packets_per_sec", "avg_packet_size", "max_packet_size",
    "min_packet_size", "tcp_count", "udp_count", "icmp_count",
    "unique_src_ips", "unique_dst_ips", "syn_count", "ack_count",
    "fin_count", "rst_count", "psh_count", "urg_count", "syn_ratio",
    "ack_ratio", "fin_ratio", "rst_ratio", "psh_ratio", "urg_ratio"
]


def create_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)


def extract_features(timeout=1, iface="eth0"):
    """Capture packets for `timeout` seconds and extract features."""
    print(f"Capturing traffic for {timeout} second(s)...")
    packets = sniff(iface=iface, timeout=timeout)
    
    tcp_count = udp_count = icmp_count = 0
    total_size = 0
    max_size = 0
    min_size = float("inf")
    unique_src = set()
    unique_dst = set()
    syn_count = ack_count = fin_count = rst_count = psh_count = urg_count = 0
    
    for pkt in packets:
        size = len(pkt)
        total_size += size
        max_size = max(max_size, size)
        if size < min_size:
            min_size = size
        
        if IP in pkt:
            unique_src.add(pkt[IP].src)
            unique_dst.add(pkt[IP].dst)
            
            if TCP in pkt:
                tcp_count += 1
                flags = pkt[TCP].flags
                if flags & 0x02: syn_count += 1
                if flags & 0x10: ack_count += 1
                if flags & 0x01: fin_count += 1
                if flags & 0x04: rst_count += 1
                if flags & 0x08: psh_count += 1
                if flags & 0x20: urg_count += 1
            elif UDP in pkt:
                udp_count += 1
            elif ICMP in pkt:
                icmp_count += 1
    
    pkt_count = len(packets)
    avg_size = total_size / pkt_count if pkt_count > 0 else 0
    min_size = min_size if min_size != float("inf") else 0
    
    if tcp_count > 0:
        syn_ratio = syn_count / tcp_count
        ack_ratio = ack_count / tcp_count
        fin_ratio = fin_count / tcp_count
        rst_ratio = rst_count / tcp_count
        psh_ratio = psh_count / tcp_count
        urg_ratio = urg_count / tcp_count
    else:
        syn_ratio = ack_ratio = fin_ratio = rst_ratio = psh_ratio = urg_ratio = 0
    
    return [
        datetime.now().isoformat(),
        pkt_count / timeout,  # packets per second
        round(avg_size, 2), max_size, min_size,
        tcp_count, udp_count, icmp_count,
        len(unique_src), len(unique_dst),
        syn_count, ack_count, fin_count, rst_count, psh_count, urg_count,
        round(syn_ratio, 4), round(ack_ratio, 4), round(fin_ratio, 4),
        round(rst_ratio, 4), round(psh_ratio, 4), round(urg_ratio, 4)
    ]


def write_csv(row):
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def main():
    create_csv()
    samples = 700
    for i in range(samples):
        row = extract_features(timeout=1)  # 1-second capture
        write_csv(row)
        print(f"\n[{i+1}/{samples}] Sample saved.")
        time.sleep(1)
    print("\nDone.")


if __name__ == "__main__":
    main()