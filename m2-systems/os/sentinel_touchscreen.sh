#!/usr/bin/env bash
# ==============================================================================
# BlackBox Sentinel — Touchscreen & Kiosk OS Display Setup
# Hardware: 4"/5" 800x480 LCD Panel (DPI/DSI/HDMI or SPI Framebuffer /dev/fb0)
# ==============================================================================

set -euo pipefail

echo "[SENTINEL-OS] Configuring 800x480 Tactical Touchscreen Display & Kiosk OS..."

# 1. Update config.txt with 800x480 resolution timings if running on Raspberry Pi
CONFIG_TXT="/boot/firmware/config.txt"
[ ! -f "$CONFIG_TXT" ] && CONFIG_TXT="/boot/config.txt"

if [ -f "$CONFIG_TXT" ]; then
    echo "[SENTINEL-OS] Adding display resolution timings to $CONFIG_TXT..."
    
    if ! grep -q "hdmi_cvt 800 480" "$CONFIG_TXT"; then
        cat << 'EOF' >> "$CONFIG_TXT"

# === BlackBox Sentinel Tactical Display (800x480 60Hz) ===
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 800 480 60 6 0 0 0
hdmi_drive=1
display_rotate=0
disable_overscan=1
gpu_mem=64
EOF
    fi
fi

# 2. Configure autologin on tty1 for Sentinel GUI kiosk
mkdir -p /etc/systemd/system/getty@tty1.service.d/
cat << 'EOF' > /etc/systemd/system/getty@tty1.service.d/autologin.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin sentinel --noclear %I $TERM
EOF

# 3. Setup X11/Cage/Chromium Kiosk launch script for sentinel user
mkdir -p /opt/blackbox-sentinel/bin
cat << 'EOF' > /opt/blackbox-sentinel/bin/launch_gui.sh
#!/usr/bin/env bash
# Launch Sentinel Touchscreen Web OS in standalone kiosk mode
export DISPLAY=:0
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Start background server
/opt/blackbox-sentinel/venv/bin/python /opt/blackbox-sentinel/m4-gui-venture/server.py &
sleep 2

# Launch Chromium in fullscreen touch kiosk
if command -v chromium-browser &>/dev/null; then
    exec chromium-browser --kiosk --noerrdialogs --disable-infobars --check-for-update-interval=31536000 --touch-events=enabled http://localhost:8080
elif command -v chromium &>/dev/null; then
    exec chromium --kiosk --noerrdialogs --disable-infobars --touch-events=enabled http://localhost:8080
elif command -v google-chrome &>/dev/null; then
    exec google-chrome --kiosk --noerrdialogs --disable-infobars --touch-events=enabled http://localhost:8080
else
    # Fallback to direct Python Native GUI
    exec /opt/blackbox-sentinel/venv/bin/python /opt/blackbox-sentinel/m4-gui-venture/src/app.py
fi
EOF
chmod +x /opt/blackbox-sentinel/bin/launch_gui.sh

echo "[SENTINEL-OS] ✅ Touchscreen & Kiosk OS configuration complete."
