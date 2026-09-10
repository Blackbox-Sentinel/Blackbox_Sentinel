import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to kill splash screen...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Disable plymouth and plymouth-quit-wait.service which is causing the hang
    cmd = """echo '1234' | sudo -S systemctl disable plymouth-quit-wait.service && \
             echo '1234' | sudo -S systemctl disable plymouth-read-write.service && \
             echo '1234' | sudo -S systemctl stop plymouth-quit-wait.service"""
             
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("[+] Splash screen killed. Terminal should drop to login or desktop.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
