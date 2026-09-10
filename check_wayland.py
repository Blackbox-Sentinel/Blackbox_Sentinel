import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    stdin, stdout, stderr = ssh.exec_command("echo $XDG_SESSION_TYPE")
    print("SESSION TYPE:")
    print(stdout.read().decode())
    
    stdin, stdout, stderr = ssh.exec_command("cat /usr/share/X11/xorg.conf.d/99-calibration.conf 2>/dev/null")
    print("CALIBRATION CONF:")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == '__main__':
    run()
