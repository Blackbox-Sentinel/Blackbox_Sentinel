import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    stdin, stdout, stderr = ssh.exec_command("cat /boot/firmware/config.txt | grep -i hdmi")
    print("CONFIG TXT (hdmi):")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == '__main__':
    run()
