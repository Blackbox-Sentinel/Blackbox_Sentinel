#!/bin/bash
# BlackBox Sentinel Kiosk Launcher

# Disable screen blanking
export DISPLAY=:0
xset s noblank
xset s off
xset -dpms

# Kill existing chromium processes so it doesn't IPC and exit immediately
killall -9 chromium-browser chromium 2>/dev/null || true
rm -rf /home/sentinel/.config/chromium/Singleton* 2>/dev/null || true

# Start the Flask Backend in the background
/usr/bin/python3 /home/sentinel/Blackbox_Sentinel/app_web.py &
FLASK_PID=$!

# Wait for Flask to boot
sleep 5

# Launch Chromium in Kiosk mode
chromium-browser \
  --noerrdialogs \
  --disable-infobars \
  --kiosk \
  --app=http://localhost:5000/ \
  --window-size=800,480 \
  --window-position=0,0 &
CHROMIUM_PID=$!

# If either the backend or the frontend crashes, exit so Systemd can restart everything
wait -n $FLASK_PID $CHROMIUM_PID
