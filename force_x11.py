import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to force X11 over Wayland...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Force X11 instead of Wayland. Wayland completely ignores the SPI screen drivers.
    cmd = """echo '12345' | sudo -S raspi-config nonint do_wayland W1 && \
             echo '12345' | sudo -S reboot"""
             
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("[+] Disabled Wayland. Rebooting into X11 Desktop...")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
