import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to route console to SPI screen...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Add fbcon=map:10 to route boot text to the SPI screen (/dev/fb1)
    cmd = """echo '1234' | sudo -S sed -i '1 s/$/ fbcon=map:10/' /boot/cmdline.txt && \
             echo '1234' | sudo -S sed -i '1 s/$/ fbcon=map:10/' /boot/firmware/cmdline.txt && \
             echo '1234' | sudo -S shutdown -h now"""
             
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("[+] Fixed! Pi is now safely shutting down.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
