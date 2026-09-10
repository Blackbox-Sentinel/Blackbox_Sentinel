import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to test sudo and force reboot...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Force an immediate ungraceful reboot using SysRq trigger
    cmd = """echo '12345' | sudo -S sh -c 'echo 1 > /proc/sys/kernel/sysrq' && \
             echo '12345' | sudo -S sh -c 'echo b > /proc/sysrq-trigger'"""
             
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("[+] SysRq forced reboot signal sent!")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
