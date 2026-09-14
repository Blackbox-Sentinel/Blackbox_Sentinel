#!/bin/bash
export DISPLAY=:0
export XAUTHORITY=/home/sentinel/.Xauthority
export QT_QPA_PLATFORM=xcb
xinput set-prop 'ADS7846 Touchscreen' 'Coordinate Transformation Matrix' 0 -1 1 1 0 0 0 0 1 2>/dev/null || true
matchbox-window-manager -use_titlebar no &
sleep 1
exec /usr/bin/python3 /home/sentinel/Blackbox_Sentinel/tools/touch_calibrate.py > /tmp/calib.log 2>&1
