import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to fix RPC network hang...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Disable RPC and NFS which cause network hangs on Pi
    cmd = """echo '12345' | sudo -S systemctl disable rpcbind && \
             echo '12345' | sudo -S systemctl disable nfs-common && \
             echo '12345' | sudo -S systemctl mask rpc-statd-notify.service && \
             echo '12345' | sudo -S systemctl restart lightdm"""
    
    stdin, stdout, stderr = client.exec_command(cmd)
    
    exit_status = stdout.channel.recv_exit_status()
    print("[+] Disabled network waits. GUI should load.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
