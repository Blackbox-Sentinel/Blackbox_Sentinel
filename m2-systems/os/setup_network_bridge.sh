#!/usr/bin/env bash
# ==============================================================================
# BlackBox Sentinel — Transparent Layer-2 Inline Bridge Setup
# Hardware Configuration:
#   - eth0: Inbound network port (facing Protected Subnet / Server)
#   - eth1: Outbound network port (facing External Router / Switch)
#   - br0:  Transparent Software Bridge with Promiscuous Monitoring
# ==============================================================================

set -euo pipefail

ETH_IN="${1:-eth0}"
ETH_OUT="${2:-eth1}"
BRIDGE_IF="br0"

echo "[SENTINEL-OS] Initializing Inline Network Bridge ($BRIDGE_IF spanning $ETH_IN <-> $ETH_OUT)..."

# 1. Ensure required networking packages are present
if ! command -v brctl &> /dev/null && ! command -v ip &> /dev/null; then
    echo "[SENTINEL-OS] Installing bridge-utils and iproute2..."
    apt-get update -qq && apt-get install -y -qq bridge-utils iproute2 ethtool
fi

# 2. Check if interfaces exist
for iface in "$ETH_IN" "$ETH_OUT"; do
    if ! ip link show "$iface" &> /dev/null; then
        echo "[WARNING] Physical interface $iface not found. Creating fallback dummy for test."
        ip link add "$iface" type dummy 2>/dev/null || true
    fi
done

# 3. Teardown existing bridge if present
if ip link show "$BRIDGE_IF" &> /dev/null; then
    echo "[SENTINEL-OS] Tearing down existing $BRIDGE_IF..."
    ip link set "$BRIDGE_IF" down || true
    ip link delete "$BRIDGE_IF" type bridge || true
fi

# 4. Create and configure bridge
echo "[SENTINEL-OS] Creating bridge $BRIDGE_IF..."
ip link add name "$BRIDGE_IF" type bridge

# Disable Spanning Tree Protocol (STP) to eliminate the 30-second listening/learning delay
ip link set dev "$BRIDGE_IF" type bridge stp_state 0
ip link set dev "$BRIDGE_IF" type bridge forward_delay 0

# 5. Enslave interfaces to bridge and put in promiscuous mode
for iface in "$ETH_IN" "$ETH_OUT"; do
    echo "[SENTINEL-OS] Enslaving $iface to $BRIDGE_IF..."
    # Flush existing IP addresses from member interfaces (they operate at L2)
    ip addr flush dev "$iface" || true
    ip link set dev "$iface" master "$BRIDGE_IF"
    ip link set dev "$iface" promisc on
    ip link set dev "$iface" up
done

# 6. Bring up bridge interface in promiscuous mode for Scapy sniffing
ip link set dev "$BRIDGE_IF" promisc on
ip link set dev "$BRIDGE_IF" up

# 7. Configure persistent systemd-networkd definition
mkdir -p /etc/systemd/network/
cat <<EOF > /etc/systemd/network/20-sentinel-bridge.netdev
[NetDev]
Name=$BRIDGE_IF
Kind=bridge

[Bridge]
STP=no
ForwardDelaySec=0
EOF

cat <<EOF > /etc/systemd/network/25-sentinel-members.network
[Match]
Name=$ETH_IN $ETH_OUT

[Network]
Bridge=$BRIDGE_IF
EOF

cat <<EOF > /etc/systemd/network/30-sentinel-bridge.network
[Match]
Name=$BRIDGE_IF

[Network]
LinkLocalAddressing=no
IPv6AcceptRA=no
EOF

echo "[SENTINEL-OS] ✅ Inline Bridge $BRIDGE_IF configured successfully."
ip link show "$BRIDGE_IF"
