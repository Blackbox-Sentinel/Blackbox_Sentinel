import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    print("[*] Changing GPU frame buffer resolution to 800x533 (zoomed out)...")
    
    cmd = f"echo '{PASSWORD}' | sudo -S sed -i 's/hdmi_cvt 480 320/hdmi_cvt 800 533/g' /boot/firmware/config.txt"
    ssh.exec_command(cmd)
    
    # Fallback in case it's in /boot/config.txt
    cmd2 = f"echo '{PASSWORD}' | sudo -S sed -i 's/hdmi_cvt 480 320/hdmi_cvt 800 533/g' /boot/config.txt"
    ssh.exec_command(cmd2)
    
    print("[*] Rebooting the Pi to apply new resolution...")
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S reboot now")
    
    ssh.close()

if __name__ == '__main__':
    run()
