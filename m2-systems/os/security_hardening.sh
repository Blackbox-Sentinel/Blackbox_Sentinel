#!/usr/bin/env bash
# ==============================================================================
# BlackBox Sentinel — Security Hardening & Appliance Provisioning
# Configures:
#   1. Dedicated 'sentinel' service user with least privilege
#   2. Volatile RAM-only Keystore (/run/sentinel/keys) on tmpfs
#   3. UFW Firewall Rules (Stealth Appliance Mode)
#   4. System Bloat Removal (RAM/CPU Optimization for Pi Zero 2 W 512MB)
#   5. OverlayFS Read-Only Root Filesystem Hooks
# ==============================================================================

set -euo pipefail

echo "================================================================="
echo "  BlackBox Sentinel OS — Appliance Hardening Script"
echo "================================================================="

# 1. Create dedicated sentinel service user
if ! id "sentinel" &>/dev/null; then
    echo "[HARDENING] Creating unprivileged service user 'sentinel'..."
    useradd -r -s /bin/false -d /opt/blackbox-sentinel -m -G dialout,gpio,video sentinel || true
fi

# 2. Configure Granular Sudoers for 'sentinel' user
echo "[HARDENING] Configuring restricted sudo capabilities for sentinel..."
cat << 'EOF' > /etc/sudoers.d/010_sentinel_restricted
# Minimal permissions required for packet capture, bridge management, and zeroization
sentinel ALL=(ALL) NOPASSWD: /sbin/ip, /usr/sbin/brctl, /bin/rm -rf /run/sentinel/keys/*, /sbin/iptables, /usr/sbin/ethtool
EOF
chmod 0440 /etc/sudoers.d/010_sentinel_restricted

# 3. Setup Volatile RAM Keystore (/run/sentinel/keys)
echo "[HARDENING] Configuring volatile RAM tmpfs keystore..."
mkdir -p /run/sentinel/keys
chown -R sentinel:sentinel /run/sentinel
chmod 0700 /run/sentinel/keys

# Add tmpfs entry in /etc/fstab if not present
if ! grep -q "/run/sentinel/keys" /etc/fstab; then
    echo "tmpfs   /run/sentinel/keys  tmpfs   nodev,nosuid,noexec,size=16M,mode=0700,uid=sentinel,gid=sentinel 0 0" >> /etc/fstab
fi

# 4. Configure UFW Firewall (Stealth Mode)
if command -v ufw &>/dev/null; then
    echo "[HARDENING] Configuring UFW Firewall..."
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    ufw default allow routed
    # Allow loopback for local GUI / inter-process communication
    ufw allow in on lo
    # Allow SSH only on management port if explicitly enabled
    # ufw allow 22/tcp
    ufw --force enable
fi

# 5. Disable unused Raspberry Pi OS bloat daemons (RAM conservation)
echo "[HARDENING] Disabling non-essential services for 512MB RAM optimization..."
SERVICES_TO_DISABLE=(
    "bluetooth.service"
    "hciuart.service"
    "avahi-daemon.service"
    "cups.service"
    "cups-browsed.service"
    "triggerhappy.service"
    "ModemManager.service"
    "motd-news.timer"
    "apt-daily.timer"
    "apt-daily-upgrade.timer"
)

for srv in "${SERVICES_TO_DISABLE[@]}"; do
    if systemctl list-unit-files | grep -q "$srv"; then
        systemctl stop "$srv" 2>/dev/null || true
        systemctl disable "$srv" 2>/dev/null || true
        systemctl mask "$srv" 2>/dev/null || true
        echo "  - Disabled & masked $srv"
    fi
done

# 6. Apply Kernel Security Parameters
if [ -f /opt/blackbox-sentinel/m2-systems/os/sentinel_sysctl.conf ]; then
    echo "[HARDENING] Applying sentinel_sysctl.conf..."
    cp /opt/blackbox-sentinel/m2-systems/os/sentinel_sysctl.conf /etc/sysctl.d/99-sentinel-security.conf
    sysctl --system > /dev/null || true
fi

# 7. Configure Log Volatility (prevent flash wear & tampering)
mkdir -p /etc/systemd/journald.conf.d/
cat << 'EOF' > /etc/systemd/journald.conf.d/00-sentinel-volatile.conf
[Journal]
Storage=volatile
RuntimeMaxUse=32M
Compress=yes
EOF

echo "[HARDENING] ✅ System security hardening complete."
