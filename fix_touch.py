import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

conf = """Section "InputClass"
        Identifier "calibration"
        MatchProduct "ADS7846 Touchscreen"
        Option "CalibrationMatrix" "-1 0 1 0 1 0 0 0 1"
EndSection
"""

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    print("[*] Deploying touch calibration matrix to fix inverted axes...")
    
    cmd = f"echo '{PASSWORD}' | sudo -S bash -c \"echo '{conf}' > /etc/X11/xorg.conf.d/99-calibration.conf\""
    ssh.exec_command(cmd)
    
    print("[*] Rebooting the Pi to apply touch calibration...")
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S reboot now")
    
    ssh.close()

if __name__ == '__main__':
    run()
