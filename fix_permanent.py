import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    # 1. Apply it live immediately so the user can use the screen right now
    matrix = "0 -1 1 -1 0 1 0 0 1"
    ssh.exec_command(f'DISPLAY=:0 xinput set-prop "ADS7846 Touchscreen" "Coordinate Transformation Matrix" {matrix}')
    
    # 2. Write it permanently to the correct X11 config that evdev uses
    conf = f"""Section "InputClass"
        Identifier "calibration"
        MatchProduct "ADS7846 Touchscreen"
        Option "CalibrationMatrix" "{matrix}"
EndSection
"""
    # X11 reads from /etc/X11/xorg.conf.d/
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S mkdir -p /etc/X11/xorg.conf.d")
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c \"echo '{conf}' > /etc/X11/xorg.conf.d/99-calibration.conf\"")
    
    # LCD-show usually overrides by putting a file in /usr/share/X11/xorg.conf.d/
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c \"echo '{conf}' > /usr/share/X11/xorg.conf.d/99-calibration.conf\"")

    ssh.close()

if __name__ == '__main__':
    run()
