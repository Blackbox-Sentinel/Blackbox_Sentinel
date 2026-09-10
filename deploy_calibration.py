import paramiko
import socket
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ip = socket.gethostbyname(HOSTNAME)
    client.connect(ip, username=USERNAME, password=PASSWORD, timeout=5)
except Exception:
    sys.exit(1)

conf = """Section "InputClass"
        Identifier "ADS7846 Touchscreen Calibration"
        MatchProduct "ADS7846 Touchscreen"
        Option "CalibrationMatrix" "-1 0 1 0 1 0 0 0 1"
EndSection
"""

print("[*] Deploying touch calibration matrix to invert X-axis...")
client.exec_command(f"echo '{conf}' | sudo -S tee /usr/share/X11/xorg.conf.d/99-calibration.conf")

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

client.close()
