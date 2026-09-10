import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("[*] Connecting to read Xorg logs...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Dump the Xorg logs to see why the GUI isn't starting
    cmd = "cat /var/log/Xorg.0.log"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    # Read the output, filtering for EE (errors) or WW (warnings)
    lines = stdout.readlines()
    print("[*] X11 Errors:")
    for line in lines:
        if "(EE)" in line or "(WW)" in line:
            print(line.strip())
            
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
