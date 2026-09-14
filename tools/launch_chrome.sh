#!/bin/bash
export DISPLAY=:0
export XAUTHORITY=/home/sentinel/.Xauthority
export QT_QPA_PLATFORM=xcb
# Enable touch input via libinput/evdev on the Pi's SPI touchscreen
export QT_QPA_EVDEV_TOUCHSCREEN_PARAMETERS=/dev/input/event0:rotate=90
export QT_ASSUME_STDERR_HAS_CONSOLE=1
matchbox-window-manager -use_titlebar no &
sleep 1
exec /usr/bin/python3 /home/sentinel/Blackbox_Sentinel/gui/dashboard.py --telemetry-file /home/sentinel/Blackbox_Sentinel/logs_and_data/phase2_telemetry_protocol_state_20260912.jsonl > /tmp/dashboard.log 2>&1

