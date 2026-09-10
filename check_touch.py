import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    # Let's check xinput list
    stdin, stdout, stderr = ssh.exec_command("DISPLAY=:0 xinput list")
    print("XINPUT:")
    print(stdout.read().decode())
    
    # If that fails, check the Xorg log
    stdin, stdout, stderr = ssh.exec_command("cat /var/log/Xorg.0.log | grep -i 'touch'")
    print("XORG LOG:")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == '__main__':
    run()
