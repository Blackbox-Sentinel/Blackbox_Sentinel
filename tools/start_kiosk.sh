#!/bin/bash
# BlackBox Sentinel Kiosk Launcher

# Kill existing processes
killall -9 python3 chromium-browser chromium xinit Xorg 2>/dev/null || true
rm -rf /home/sentinel/.config/chromium/Singleton* 2>/dev/null || true
rm -f /tmp/.X0-lock /tmp/.X1-lock /tmp/.X11-unix/X0 2>/dev/null || true

# Host network disabled per user request - only running PyQt6 dashboard natively

# Launch Chromium in Kiosk mode AS SENTINEL, inside a dedicated X11 Server running AS ROOT
xinit /usr/bin/su - sentinel -c "/bin/bash /home/sentinel/Blackbox_Sentinel/tools/launch_chrome.sh" -- :0 -ac -s 0 dpms -nocursor vt7 > /tmp/xinit.log 2>&1 &
XINIT_PID=$!

# Just wait indefinitely. Systemd will kill the entire cgroup if the service is stopped.
wait
