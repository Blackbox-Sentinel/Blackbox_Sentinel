#!/usr/bin/env python3
"""Fix /boot/firmware/config.txt: remove old Sentinel UART config, add uart5 overlay."""

CONFIG = '/boot/firmware/config.txt'

with open(CONFIG) as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if 'BlackBox Sentinel UART' in line or 'BlackBox Sentinel:' in line:
        skip = True
        continue
    if skip:
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('dtoverlay=disable-bt') or stripped.startswith('enable_uart') or stripped.startswith('dtoverlay=uart'):
            continue
        if stripped == '':
            skip = False
            continue
        skip = False
    new_lines.append(line)

# Remove trailing blank lines
while new_lines and new_lines[-1].strip() == '':
    new_lines.pop()

new_lines.append('\n\n')
new_lines.append('# BlackBox Sentinel: UART5 on GPIO 12/13 for ESP32 Bridge\n')
new_lines.append('# UART5 maps TX=GPIO12 RX=GPIO13 -> creates /dev/ttyAMA5\n')
new_lines.append('dtoverlay=uart5\n')
new_lines.append('enable_uart=1\n')

with open(CONFIG, 'w') as f:
    f.writelines(new_lines)

print("config.txt updated with uart5 overlay")
