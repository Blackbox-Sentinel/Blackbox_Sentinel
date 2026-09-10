import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to completely remove splash screen...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Remove 'splash' and 'quiet' from cmdline.txt so it shows raw Linux terminal boot logs
    cmd = """echo '1234' | sudo -S sed -i 's/splash//g' /boot/cmdline.txt && \
             echo '1234' | sudo -S sed -i 's/quiet//g' /boot/cmdline.txt && \
             echo '1234' | sudo -S sed -i 's/splash//g' /boot/firmware/cmdline.txt && \
             echo '1234' | sudo -S sed -i 's/quiet//g' /boot/firmware/cmdline.txt && \
             echo '1234' | sudo -S reboot"""
             
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("[+] Splash screen eradicated from boot sequence. Rebooting.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
