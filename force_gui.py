import paramiko
import time

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Fixing Boot to Desktop...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
    
    # B4 = Desktop GUI, automatically logged in as the current user
    cmd = "echo '1234' | sudo -S raspi-config nonint do_boot_behaviour B4 && echo '1234' | sudo -S systemctl restart lightdm"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    # Wait for completion
    exit_status = stdout.channel.recv_exit_status()
    print("[+] GUI forced. LightDM restarted.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
