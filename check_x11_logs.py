import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to read X11 error logs...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    cmd = "cat /var/log/Xorg.0.log | grep -E '(EE|WW)'"
    stdin, stdout, stderr = client.exec_command(cmd)
    print("X11 Log (EE/WW):")
    print(stdout.read().decode())
    
    cmd2 = "systemctl status lightdm --no-pager"
    stdin2, stdout2, stderr2 = client.exec_command(cmd2)
    print("LightDM Status:")
    print(stdout2.read().decode('utf-8', 'ignore'))
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
