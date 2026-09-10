import paramiko

HOSTNAME = 'sentinel.local'
USERNAME = 'admin'
PASSWORD = '12345'

def check_pi():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    # Check if LCD-show directory exists
    stdin, stdout, stderr = ssh.exec_command("ls -la LCD-show")
    print("LCD-show directory contents:")
    print(stdout.read().decode())
    
    # Check git clone logs
    stdin, stdout, stderr = ssh.exec_command("cat /var/log/syslog | grep LCD")
    print("Syslog LCD:")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == '__main__':
    check_pi()
