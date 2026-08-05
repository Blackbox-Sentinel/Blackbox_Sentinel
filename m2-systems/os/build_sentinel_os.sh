#!/usr/bin/env bash
# ==============================================================================
# BlackBox Sentinel — Master OS Provisioner & Appliance Builder
# Target: Raspberry Pi Zero 2 W / Debian 12 (Bookworm) 64-bit Lite
#
# This script provisions a standard minimal Linux image into a dedicated,
# security-hardened BlackBox Sentinel Autonomous Edge Defense Node (AEDN).
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}======================================================================${NC}"
echo -e "${CYAN}       🛡️  BLACKBOX SENTINEL OS — APPLIANCE PROVISIONER  🛡️          ${NC}"
echo -e "${BLUE}======================================================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] This provisioning script must be run as root (sudo).${NC}"
    exit 1
fi

SENTINEL_ROOT="/opt/blackbox-sentinel"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_SRC="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "\n${GREEN}[STEP 1/7] Updating Base OS & Installing Core System Dependencies...${NC}"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-tk \
    bridge-utils \
    iproute2 \
    ethtool \
    tcpdump \
    libpcap-dev \
    iptables \
    ufw \
    git \
    libatlas-base-dev \
    libopenblas-dev \
    xserver-xorg \
    xinit \
    x11-xserver-utils

echo -e "\n${GREEN}[STEP 2/7] Deploying BlackBox Sentinel Codebase to $SENTINEL_ROOT...${NC}"
mkdir -p "$SENTINEL_ROOT"
cp -r "$REPO_SRC"/* "$SENTINEL_ROOT"/ 2>/dev/null || true
mkdir -p "$SENTINEL_ROOT/m3-ml-ledger/data" "$SENTINEL_ROOT/m3-ml-ledger/models"

echo -e "\n${GREEN}[STEP 3/7] Setting up Isolated Python Environment & ML Libraries...${NC}"
python3 -m venv "$SENTINEL_ROOT/venv"
"$SENTINEL_ROOT/venv/bin/pip" install --upgrade pip -q
"$SENTINEL_ROOT/venv/bin/pip" install -q \
    scapy \
    numpy \
    pandas \
    scikit-learn \
    joblib \
    gpiozero \
    pyserial

echo -e "\n${GREEN}[STEP 4/7] Applying System Security Hardening & Kernel Tuning...${NC}"
bash "$SENTINEL_ROOT/m2-systems/os/security_hardening.sh"

echo -e "\n${GREEN}[STEP 5/7] Configuring Hardware Display & Framebuffer Kiosk...${NC}"
bash "$SENTINEL_ROOT/m2-systems/os/sentinel_touchscreen.sh"

echo -e "\n${GREEN}[STEP 6/7] Installing Systemd Appliance Services...${NC}"
SYSTEMD_DIR="$SENTINEL_ROOT/m2-systems/os/systemd"
chmod +x "$SENTINEL_ROOT/m2-systems/os/setup_network_bridge.sh"
chmod +x "$SENTINEL_ROOT/m2-systems/os/security_hardening.sh"
chmod +x "$SENTINEL_ROOT/m2-systems/os/sentinel_touchscreen.sh"

cp "$SYSTEMD_DIR/sentinel-bridge.service" /etc/systemd/system/
cp "$SYSTEMD_DIR/sentinel-core.service" /etc/systemd/system/
cp "$SYSTEMD_DIR/sentinel-gui.service" /etc/systemd/system/
cp "$SYSTEMD_DIR/sentinel.target" /etc/systemd/system/

systemctl daemon-reload
systemctl enable sentinel-bridge.service
systemctl enable sentinel-core.service
systemctl enable sentinel-gui.service
systemctl enable sentinel.target

echo -e "\n${GREEN}[STEP 7/7] Verifying System Permissions & Keystore Paths...${NC}"
mkdir -p /run/sentinel/keys
chown -R sentinel:sentinel "$SENTINEL_ROOT/m3-ml-ledger/data"
chown -R sentinel:sentinel "$SENTINEL_ROOT/m3-ml-ledger/models"
chown -R sentinel:sentinel /run/sentinel

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${GREEN}  ✅  BlackBox Sentinel OS Provisioning Complete!                    ${NC}"
echo -e "${CYAN}  System will start in transparent inline mode on next boot.          ${NC}"
echo -e "${CYAN}  To start manually now: systemctl start sentinel.target               ${NC}"
echo -e "${BLUE}======================================================================${NC}"
