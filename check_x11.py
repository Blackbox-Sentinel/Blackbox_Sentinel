import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to check LightDM status...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Check if lightdm is failing
    cmd = "systemctl status lightdm --no-pager"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("LightDM Status:\n", stdout.read().decode())
    
    cmd2 = "cat /var/log/Xorg.0.log | grep EE"
    stdin2, stdout2, stderr2 = client.exec_command(cmd2)
    print("Xorg Errors:\n", stdout2.read().decode())
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
