import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    stdin, stdout, stderr = ssh.exec_command("DISPLAY=:0 xinput list")
    with open("xinput_log.txt", "w", encoding="utf-8") as f:
        f.write(stdout.read().decode('utf-8', errors='ignore'))
        
    stdin, stdout, stderr = ssh.exec_command("cat /var/log/Xorg.0.log | grep -i 'touch'")
    with open("xorg_log.txt", "w", encoding="utf-8") as f:
        f.write(stdout.read().decode('utf-8', errors='ignore'))
        
    ssh.close()

if __name__ == '__main__':
    run()
