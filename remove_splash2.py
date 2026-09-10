import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to completely remove splash screen...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Remove 'splash' so Plymouth never starts and fights LightDM for the screen
    cmd = """echo '12345' | sudo -S sed -i 's/splash//g' /boot/cmdline.txt && \
             echo '12345' | sudo -S sed -i 's/splash//g' /boot/firmware/cmdline.txt && \
             echo '12345' | sudo -S systemctl disable plymouth && \
             echo '12345' | sudo -S reboot"""
             
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("[+] Splash screen eradicated from boot sequence. Rebooting.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
