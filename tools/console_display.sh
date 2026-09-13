#!/bin/bash
# BlackBox Sentinel — Console Status Display
# Shows a clean status screen on the physical display (TTY1)
# Run as a service on TTY1 so the physical screen shows useful info instead of boot logs.

clear

PI_IP=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)

# Hide cursor
printf '\033[?25l'

show_status() {
    clear
    printf '\033[1;36m'  # Cyan bold
    echo ""
    echo "  ████████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗"
    echo "  ╚══██╔══╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║"
    echo "     ██║   █████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║"
    echo "     ██║   ██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║"
    echo "     ██║   ███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗"
    echo "     ╚═╝   ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝"
    printf '\033[0m'
    echo ""
    printf '\033[1;37m'
    echo "  ┌─────────────────────────────────────────────────────┐"
    echo "  │         BlackBox Sentinel — Edge Defense Node        │"
    echo "  │              RUNNING IN HEADLESS MODE                │"
    echo "  ├─────────────────────────────────────────────────────┤"
    printf '\033[1;32m'
    printf "  │  Web UI:  http://%-35s│\n" "${PI_IP}:5000 "
    printf "  │  Node:    %-38s│\n" "${HOSTNAME} "
    printf "  │  Time:    %-38s│\n" "$(date '+%H:%M:%S  %A, %B %d %Y') "
    printf '\033[0m'
    
    # Check Flask
    if curl -s --max-time 1 http://localhost:5000/api/system_stats > /tmp/.sentinel_check 2>/dev/null; then
        CPU=$(python3 -c "import json; d=json.load(open('/tmp/.sentinel_check')); print(d.get('cpu','?'))" 2>/dev/null)
        TEMP=$(python3 -c "import json; d=json.load(open('/tmp/.sentinel_check')); print(d.get('temp','?'))" 2>/dev/null)
        printf '\033[1;32m'
        printf "  │  Status:  %-38s│\n" "✓ Flask ONLINE | CPU: ${CPU}% | Temp: ${TEMP}°C"
    else
        printf '\033[1;31m'
        printf "  │  Status:  %-38s│\n" "✗ Flask STARTING..."
    fi
    
    # ESP32 UART check
    if python3 -c "import serial; s=serial.Serial('/dev/ttyAMA5',115200,timeout=1); s.write(b'PING\n'); import time; time.sleep(0.5); r=s.read(s.in_waiting); s.close(); exit(0 if b'pong' in r else 1)" 2>/dev/null; then
        printf '\033[1;32m'
        printf "  │  ESP32:   %-38s│\n" "✓ UART5 LINK OK (GPIO12/13)"
    else
        printf '\033[1;33m'
        printf "  │  ESP32:   %-38s│\n" "~ ESP32 UART (no response)"
    fi
    
    printf '\033[1;37m'
    echo "  └─────────────────────────────────────────────────────┘"
    printf '\033[0;37m'
    echo ""
    echo "  Access the full UI from any browser on your network:"
    printf '\033[1;33m'
    echo "    http://${PI_IP}:5000"
    printf '\033[0m'
    echo ""
    echo "  [Updates every 10s] [SSH: sentinel@${HOSTNAME}.local]"
}

# Loop forever - refresh every 10 seconds
while true; do
    show_status
    sleep 10
done
