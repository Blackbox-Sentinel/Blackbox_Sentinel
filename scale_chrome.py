import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    # Modify the default Chromium launch arguments to force a 60% scale factor
    cmd = f"echo '{PASSWORD}' | sudo -S sed -i 's/Exec=\\/usr\\/bin\\/chromium-browser/Exec=\\/usr\\/bin\\/chromium-browser --force-device-scale-factor=0.6/g' /usr/share/applications/chromium-browser.desktop"
    ssh.exec_command(cmd)
    
    # Just in case it's named chromium.desktop instead
    cmd2 = f"echo '{PASSWORD}' | sudo -S sed -i 's/Exec=\\/usr\\/bin\\/chromium/Exec=\\/usr\\/bin\\/chromium --force-device-scale-factor=0.6/g' /usr/share/applications/chromium.desktop"
    ssh.exec_command(cmd2)

    ssh.close()
    print("Chromium UI scaling fixed!")

if __name__ == '__main__':
    run()
