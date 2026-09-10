import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    cmd = f"echo '{PASSWORD}' | sudo -S grep 'hdmi_cvt' /boot/firmware/config.txt"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print("CONFIG TXT (hdmi):")
    print(stdout.read().decode())
    
    cmd = f"echo '{PASSWORD}' | sudo -S sed -i 's/hdmi_cvt 480 320/hdmi_cvt 800 533/g' /boot/firmware/config.txt"
    ssh.exec_command(cmd)
    
    cmd = f"echo '{PASSWORD}' | sudo -S sed -i 's/hdmi_cvt 480 320/hdmi_cvt 800 533/g' /boot/config.txt"
    ssh.exec_command(cmd)
    
    print("Issuing reboot...")
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S reboot now")
    
    ssh.close()

if __name__ == '__main__':
    run()
