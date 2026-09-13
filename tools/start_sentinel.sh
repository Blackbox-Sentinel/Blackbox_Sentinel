#!/bin/bash
# BlackBox Sentinel — Headless Launcher
# Runs Flask backend only. Access UI at http://<pi-ip>:5000 from any browser.
# No display/X11/Chromium required.

PROJECT=/home/sentinel/Blackbox_Sentinel
LOG=/tmp/flask.log

# Fix log file permissions (may be owned by root from prior run)
rm -f "$LOG" 2>/dev/null || true
touch "$LOG" && chmod 666 "$LOG" 2>/dev/null || true

# Kill any existing flask instance
pkill -f "python3 app_web.py" 2>/dev/null || true
sleep 1

echo "[SENTINEL] Starting BlackBox Sentinel headless at $(date)" | tee "$LOG"
echo "[SENTINEL] UI accessible at: http://$(hostname -I | awk '{print $1}'):5000" | tee -a "$LOG"

# Run Flask directly as sentinel user
exec su - sentinel -c "
  cd ${PROJECT}
  export SENTINEL_HARDWARE=hw
  export PYTHONUNBUFFERED=1
  exec /usr/bin/python3 app_web.py
" >> "$LOG" 2>&1
