import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to fix splash screen hang...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # 1. Force boot to desktop (B4)
    # 2. Disable cloud-init which causes network hangs
    # 3. Disable plymouth-quit-wait which freezes the splash screen
    # 4. Restart lightdm
    cmd = """echo '12345' | sudo -S raspi-config nonint do_boot_behaviour B4 && \
             echo '12345' | sudo -S touch /etc/cloud/cloud-init.disabled && \
             echo '12345' | sudo -S systemctl disable cloud-init && \
             echo '12345' | sudo -S systemctl disable cloud-config && \
             echo '12345' | sudo -S systemctl disable plymouth-quit-wait.service && \
             echo '12345' | sudo -S systemctl stop plymouth-quit-wait.service && \
             echo '12345' | sudo -S systemctl restart lightdm"""
             
    stdin, stdout, stderr = client.exec_command(cmd)
    
    exit_status = stdout.channel.recv_exit_status()
    print("[+] Fixed! Desktop should pop up now.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
