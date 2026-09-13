#!/bin/bash
# BlackBox Sentinel Kiosk Launcher

# Kill existing processes
killall -9 chromium-browser chromium xinit Xorg 2>/dev/null || true
rm -rf /home/sentinel/.config/chromium/Singleton* 2>/dev/null || true
rm -f /tmp/.X0-lock /tmp/.X1-lock /tmp/.X11-unix/X0 2>/dev/null || true

# Start the Flask Backend in the background AS SENTINEL
su - sentinel -c "/usr/bin/python3 /home/sentinel/Blackbox_Sentinel/app_web.py" &
FLASK_PID=$!

# Wait for Flask to boot
sleep 5

# Launch Chromium in Kiosk mode AS SENTINEL, inside a dedicated X11 Server running AS ROOT
xinit /usr/bin/su - sentinel -c "export DISPLAY=:0 && /usr/bin/chromium-browser --noerrdialogs --disable-infobars --start-fullscreen --kiosk --force-device-scale-factor=0.6 http://localhost:5000/" -- :0 -ac -s 0 dpms -nocursor vt7 &
XINIT_PID=$!

# If either the backend or the frontend crashes, exit so Systemd can restart everything
wait -n $FLASK_PID $XINIT_PID
