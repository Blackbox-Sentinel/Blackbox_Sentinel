from scapy.all import sniff

print("Capturing 10 packets...")

packets = sniff(count=10)

print(f"Captured {len(packets)} packets.")

for packet in packets:
    print(packet.summary())