#!/bin/bash
# BlackBox Sentinel Kiosk Launcher

# Disable screen blanking
export DISPLAY=:0
xset s noblank
xset s off
xset -dpms

# Start the Flask Backend in the background
/usr/bin/python3 /home/sentinel/Blackbox_Sentinel/app_web.py &

# Wait for Flask to boot
sleep 5

# Launch Chromium in Kiosk mode
chromium-browser \
  --noerrdialogs \
  --disable-infobars \
  --kiosk \
  --app=http://localhost:5000/ \
  --window-size=800,480 \
  --window-position=0,0
