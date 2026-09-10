import paramiko
import time
import sys

HOSTNAME = 'sentinel.local'
USERNAME = 'admin'
PASSWORD = '12345'

def run_ssh():
    print(f"Connecting to {HOSTNAME}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
        print("Successfully connected to Raspberry Pi!")
        
        # We run the command to download and install the LCD driver.
        # Note: the LCD35-show script automatically reboots the Pi at the end.
        cmd = (
            "sudo rm -rf LCD-show && "
            "git clone https://github.com/goodtft/LCD-show.git && "
            "chmod -R 755 LCD-show && "
            "cd LCD-show/ && "
            "echo '12345' | sudo -S ./LCD35-show"
        )
        
        print("Downloading and installing 3.5\" Touchscreen drivers...")
        print("This will take about 2-3 minutes. The Pi will reboot automatically when finished.")
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Read the output line by line so the user can see progress
        for line in iter(stdout.readline, ""):
            print(line, end="")
            
    except Exception as e:
        print(f"Connection closed or error occurred (this is normal if it rebooted): {e}")
    finally:
        ssh.close()
        print("\nFinished! If the Pi rebooted, wait 1 minute for the screen to turn on.")

if __name__ == '__main__':
    run_ssh()
