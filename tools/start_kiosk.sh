#!/bin/bash
# BlackBox Sentinel Kiosk Launcher

# Kill existing processes
killall -9 python3 chromium-browser chromium xinit Xorg 2>/dev/null || true
rm -rf /home/sentinel/.config/chromium/Singleton* 2>/dev/null || true
rm -f /tmp/.X0-lock /tmp/.X1-lock /tmp/.X11-unix/X0 2>/dev/null || true

# Start the Flask Backend in the background AS SENTINEL
su - sentinel -c "cd /home/sentinel/Blackbox_Sentinel && /usr/bin/python3 app_web.py > /tmp/flask.log 2>&1" &
FLASK_PID=$!

# Wait for Flask to boot
sleep 5

# Launch Chromium in Kiosk mode AS SENTINEL, inside a dedicated X11 Server running AS ROOT
xinit /usr/bin/su - sentinel -c "export DISPLAY=:0 && matchbox-window-manager -use_titlebar no & /usr/bin/chromium-browser --noerrdialogs --disable-infobars --start-fullscreen --kiosk --window-size=480,320 --window-position=0,0 --force-device-scale-factor=0.6 http://localhost:5000/ > /tmp/chromium.log 2>&1 ; sleep infinity" -- :0 -ac -s 0 dpms -nocursor vt7 > /tmp/xinit.log 2>&1 &
XINIT_PID=$!

# Just wait indefinitely. Systemd will kill the entire cgroup if the service is stopped.
wait
