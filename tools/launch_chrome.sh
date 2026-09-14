#!/bin/bash
export DISPLAY=:0
export XAUTHORITY=/home/sentinel/.Xauthority
export QT_QPA_PLATFORM=xcb

# Start window manager first
matchbox-window-manager -use_titlebar no &
sleep 1

# ── Touchscreen calibration for tft35a rotated 270° (ADS7846 on event0) ──
# The transformation matrix maps raw touch coords to the rotated screen.
# For a 270° rotated display: swap axes and invert X
# Matrix: [0, -1, 1,  1, 0, 0,  0, 0, 1]
TOUCH_DEVICE="ADS7846 Touchscreen"
xinput set-prop "$TOUCH_DEVICE" "Coordinate Transformation Matrix" 0 -1 1 1 0 0 0 0 1 2>/dev/null || true
xinput set-prop "$TOUCH_DEVICE" "libinput Calibration Matrix" 0 -1 1 1 0 0 0 0 1 2>/dev/null || true

# Launch dashboard
exec /usr/bin/python3 /home/sentinel/Blackbox_Sentinel/gui/dashboard.py \
  --telemetry-file /home/sentinel/Blackbox_Sentinel/logs_and_data/phase2_telemetry_protocol_state_20260912.jsonl \
  > /tmp/dashboard.log 2>&1
