import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    # The correct matrix to swap axes and invert both
    matrix = "0 -1 1 -1 0 1 0 0 1"
    
    cmd = f'DISPLAY=:0 xinput set-prop "ADS7846 Touchscreen" "Coordinate Transformation Matrix" {matrix}'
    ssh.exec_command(cmd)
    
    # Update udev rules for persistence
    rule = f'ENV{{ID_INPUT_TOUCHSCREEN}}=="1", ENV{{LIBINPUT_CALIBRATION_MATRIX}}="{matrix}"'
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c \"echo '{rule}' > /etc/udev/rules.d/99-touchscreen.rules\"")
    
    ssh.close()

if __name__ == '__main__':
    run()
