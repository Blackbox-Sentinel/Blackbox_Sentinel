import paramiko

HOSTNAME = 'sentinel.local'
USERNAME = 'admin'
PASSWORD = '12345'

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    print("Executing LCD driver installation...")
    # Using sudo -S to pipe the password
    stdin, stdout, stderr = ssh.exec_command("cd LCD-show && echo '12345' | sudo -S ./LCD35-show")
    
    # Read the output
    print("STDOUT:")
    print(stdout.read().decode())
    print("STDERR:")
    print(stderr.read().decode())
    
    ssh.close()

if __name__ == '__main__':
    run()
