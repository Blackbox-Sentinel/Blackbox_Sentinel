import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to issue clean reboot...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Issue a proper clean reboot
    cmd = "echo '1234' | sudo -S reboot"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("[+] Clean reboot command sent.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
