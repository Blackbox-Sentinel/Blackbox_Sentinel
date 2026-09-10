import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    # Kill the full-screen touch test application
    ssh.exec_command("pkill -f touch_test.py")
    print("Closed the touch test app. Returning to Raspberry Pi OS.")
    
    ssh.close()

if __name__ == '__main__':
    run()
