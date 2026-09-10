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

# Write a local bash script on the Pi that runs independently of SSH
script = """
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock
dpkg --configure -a
apt-get install -y --fix-missing xinit xserver-xorg-legacy
sed -i 's/needs_root_rights=no/needs_root_rights=yes/g' /etc/X11/Xwrapper.config
nohup startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor >/tmp/startx.log 2>&1 &
"""

client.exec_command(f"echo '{script}' > /home/admin/install.sh")
client.exec_command("chmod +x /home/admin/install.sh")

# Execute it completely detached so it survives SSH disconnects!
client.exec_command("echo '12345' | sudo -S nohup /home/admin/install.sh >/home/admin/install.log 2>&1 &")

client.close()
print("[*] Successfully launched detached installation!")
