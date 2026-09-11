#!/usr/bin/env bash
# ==============================================================================
# BlackBox Sentinel — Virtual Network Namespace Testbed (veth lab)
# Creates a complete in-software simulated physical network:
#   [ns_client (10.0.0.10)] <---> [ns_sentinel (br0 inline)] <---> [ns_server (10.0.0.20)]
# ==============================================================================

set -euo pipefail

echo "================================================================="
echo "  BlackBox Sentinel — Setting up Linux veth Virtual Lab"
echo "================================================================="

if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] Must run as root (sudo) to manage network namespaces."
    exit 1
fi

# 1. Clean up existing namespaces if present
echo "[VETH-LAB] Cleaning up previous namespaces..."
ip netns del ns_client 2>/dev/null || true
ip netns del ns_sentinel 2>/dev/null || true
ip netns del ns_server 2>/dev/null || true

# 2. Create Namespaces
echo "[VETH-LAB] Creating network namespaces: ns_client, ns_sentinel, ns_server..."
ip netns add ns_client
ip netns add ns_sentinel
ip netns add ns_server

# 3. Create veth pairs (Virtual Ethernet Cables)
echo "[VETH-LAB] Creating virtual ethernet cable links..."
# Cable 1: Client to Sentinel (eth_cli <-> s_eth0)
ip link add eth_cli type veth peer name s_eth0
# Cable 2: Server to Sentinel (eth_srv <-> s_eth1)
ip link add eth_srv type veth peer name s_eth1

# 4. Move interfaces into respective namespaces
ip link set eth_cli netns ns_client
ip link set s_eth0 netns ns_sentinel
ip link set s_eth1 netns ns_sentinel
ip link set eth_srv netns ns_server

# 5. Configure ns_client (10.0.0.10/24)
echo "[VETH-LAB] Configuring ns_client interface..."
ip netns exec ns_client ip link set lo up
ip netns exec ns_client ip addr add 10.0.0.10/24 dev eth_cli
ip netns exec ns_client ip link set eth_cli up

# 6. Configure ns_server (10.0.0.20/24)
echo "[VETH-LAB] Configuring ns_server interface..."
ip netns exec ns_server ip link set lo up
ip netns exec ns_server ip addr add 10.0.0.20/24 dev eth_srv
ip netns exec ns_server ip link set eth_srv up

# 7. Configure ns_sentinel (Transparent Bridge br0 spanning s_eth0 and s_eth1)
echo "[VETH-LAB] Configuring ns_sentinel inline bridge..."
ip netns exec ns_sentinel ip link set lo up
ip netns exec ns_sentinel ip link add name br0 type bridge
ip netns exec ns_sentinel ip link set dev br0 type bridge stp_state 0 forward_delay 0

ip netns exec ns_sentinel ip link set s_eth0 master br0
ip netns exec ns_sentinel ip link set s_eth1 master br0

ip netns exec ns_sentinel ip link set s_eth0 promisc on up
ip netns exec ns_sentinel ip link set s_eth1 promisc on up
ip netns exec ns_sentinel ip link set br0 promisc on up

echo "================================================================="
echo "  ✅ Virtual Network Lab Ready!"
echo "  To test connectivity through Sentinel bridge:"
echo "    sudo ip netns exec ns_client ping -c 3 10.0.0.20"
echo "  To run Sentinel sniffer inside inline namespace:"
echo "    sudo ip netns exec ns_sentinel python3 sentinel_pipeline.py"
echo "================================================================="
