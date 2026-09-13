#!/bin/bash
export DISPLAY=:0
export XAUTHORITY=/home/sentinel/.Xauthority
matchbox-window-manager -use_titlebar no &
# Give the window manager a second to bind
sleep 1
exec /usr/bin/chromium-browser --noerrdialogs --disable-infobars --start-fullscreen --kiosk --window-size=480,320 --window-position=0,0 --force-device-scale-factor=0.6 http://localhost:5000/ > /tmp/chromium.log 2>&1
