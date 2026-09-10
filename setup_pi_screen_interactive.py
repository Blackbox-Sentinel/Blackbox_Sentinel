import paramiko
import time
import sys

HOSTNAME = 'sentinel.local'
USERNAME = 'admin'
PASSWORD = '12345'

def run():
    print(f"Connecting to {HOSTNAME}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    print("Connected! Starting a shell...")
    channel = ssh.invoke_shell()
    
    def wait_for_prompt():
        out = ""
        while not (out.endswith("$ ") or out.endswith("# ") or "password" in out.lower()):
            if channel.recv_ready():
                out += channel.recv(1024).decode('utf-8')
        return out

    wait_for_prompt()
    
    print("Downloading LCD drivers...")
    channel.send("git clone https://github.com/goodtft/LCD-show.git\n")
    time.sleep(5)
    
    print("Setting permissions...")
    channel.send("chmod -R 755 LCD-show\n")
    time.sleep(1)
    
    print("Installing LCD drivers (this will reboot the Pi)...")
    channel.send("cd LCD-show && sudo ./LCD35-show\n")
    time.sleep(2)
    
    out = channel.recv(1024).decode('utf-8')
    if "password" in out.lower():
        channel.send(f"{PASSWORD}\n")
    
    print("Installation running! Waiting for the Pi to reboot...")
    
    ssh.close()

if __name__ == '__main__':
    run()
