from scapy.all import sniff, IP, TCP, UDP, ICMP
import csv
import os
from datetime import datetime
import time

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_FILE = BASE_DIR / "traffic.csv"
header = [
    "timestamp",
    "packets_per_sec",

    "avg_packet_size",
    "max_packet_size",
    "min_packet_size",

    "tcp_count",
    "udp_count",
    "icmp_count",

    "unique_src_ips",
    "unique_dst_ips",

    "syn_count",
    "ack_count",
    "fin_count",
    "rst_count",
    "psh_count",
    "urg_count",

    "syn_ratio",
    "ack_ratio",
    "fin_ratio",
    "rst_ratio",
    "psh_ratio",
    "urg_ratio"
]


def create_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(header)


def extract_features():

    print("Capturing traffic for 1 second...")

    packets = sniff(timeout=1)

    tcp_count = 0
    udp_count = 0
    icmp_count = 0

    total_packet_size = 0
    max_packet_size = 0
    min_packet_size = float("inf")

    unique_src_ips = set()
    unique_dst_ips = set()

    syn_count = 0
    ack_count = 0
    fin_count = 0
    rst_count = 0
    psh_count = 0
    urg_count = 0

    for packet in packets:

        size = len(packet)

        total_packet_size += size

        if size > max_packet_size:
            max_packet_size = size

        if size < min_packet_size:
            min_packet_size = size

        if IP in packet:
            unique_src_ips.add(packet[IP].src)
            unique_dst_ips.add(packet[IP].dst)

        if TCP in packet:

            tcp_count += 1

            flags = packet[TCP].flags

            if flags & 0x02:  # SYN
                syn_count += 1

            if flags & 0x10:  # ACK
                ack_count += 1

            if flags & 0x01:  # FIN
                fin_count += 1

            if flags & 0x04:  # RST
                rst_count += 1

            if flags & 0x08:  # PSH
                psh_count += 1

            if flags & 0x20:  # URG
                urg_count += 1

        elif UDP in packet:
            udp_count += 1

        elif ICMP in packet:
            icmp_count += 1

    packet_count = len(packets)

    if packet_count > 0:
        avg_packet_size = total_packet_size / packet_count
    else:
        avg_packet_size = 0
        min_packet_size = 0

    if tcp_count > 0:
        syn_ratio = syn_count / tcp_count
        ack_ratio = ack_count / tcp_count
        fin_ratio = fin_count / tcp_count
        rst_ratio = rst_count / tcp_count
        psh_ratio = psh_count / tcp_count
        urg_ratio = urg_count / tcp_count
    else:
        syn_ratio = 0
        ack_ratio = 0
        fin_ratio = 0
        rst_ratio = 0
        psh_ratio = 0
        urg_ratio = 0

    print("\n----- FEATURES -----")
    print(f"Packets/sec            : {packet_count}")
    print(f"Average Packet Size    : {avg_packet_size:.2f} bytes")
    print(f"Maximum Packet Size    : {max_packet_size} bytes")
    print(f"Minimum Packet Size    : {min_packet_size} bytes")
    print(f"TCP Count              : {tcp_count}")
    print(f"UDP Count              : {udp_count}")
    print(f"ICMP Count             : {icmp_count}")
    print(f"Unique Source IPs      : {len(unique_src_ips)}")
    print(f"Unique Destination IPs : {len(unique_dst_ips)}")

    print("\n----- TCP FLAG COUNTS -----")
    print(f"SYN : {syn_count}")
    print(f"ACK : {ack_count}")
    print(f"FIN : {fin_count}")
    print(f"RST : {rst_count}")
    print(f"PSH : {psh_count}")
    print(f"URG : {urg_count}")

    print("\n----- TCP FLAG RATIOS -----")
    print(f"SYN Ratio : {syn_ratio:.4f}")
    print(f"ACK Ratio : {ack_ratio:.4f}")
    print(f"FIN Ratio : {fin_ratio:.4f}")
    print(f"RST Ratio : {rst_ratio:.4f}")
    print(f"PSH Ratio : {psh_ratio:.4f}")
    print(f"URG Ratio : {urg_ratio:.4f}")

    return [
        datetime.now().isoformat(),

        packet_count,

        round(avg_packet_size, 2),
        max_packet_size,
        min_packet_size,

        tcp_count,
        udp_count,
        icmp_count,

        len(unique_src_ips),
        len(unique_dst_ips),

        syn_count,
        ack_count,
        fin_count,
        rst_count,
        psh_count,
        urg_count,

        round(syn_ratio, 4),
        round(ack_ratio, 4),
        round(fin_ratio, 4),
        round(rst_ratio, 4),
        round(psh_ratio, 4),
        round(urg_ratio, 4)
    ]


def write_csv(row):
    with open(CSV_FILE, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(row)


def main():

    create_csv()

    samples = 700

    for i in range(samples):

        row = extract_features()

        write_csv(row)

        print(f"\n[{i+1}/{samples}] Sample saved.")

        time.sleep(1)

    print("\nDataset collection complete.")


if __name__ == "__main__":
    main()