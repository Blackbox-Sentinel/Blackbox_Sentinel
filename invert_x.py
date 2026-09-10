import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    # Invert the X axis using xinput dynamically
    cmd = 'DISPLAY=:0 xinput set-prop "ADS7846 Touchscreen" "Coordinate Transformation Matrix" -1 0 1 0 1 0 0 0 1'
    ssh.exec_command(cmd)
    
    # Also write it to udev rules for persistence across reboots
    rule = 'ENV{ID_INPUT_TOUCHSCREEN}=="1", ENV{LIBINPUT_CALIBRATION_MATRIX}="-1 0 1 0 1 0 0 0 1"'
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c \"echo '{rule}' > /etc/udev/rules.d/99-touchscreen.rules\"")
    
    ssh.close()

if __name__ == '__main__':
    run()
