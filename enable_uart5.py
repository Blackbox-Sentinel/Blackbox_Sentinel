import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('sentinel.local', username='admin', password='12345', timeout=5)

# 1. Enable UART5 overlay (GPIO 12=TX, GPIO 13=RX on Pi 4)
cmd = 'echo 12345 | sudo -S bash -c "echo dtoverlay=uart5 >> /boot/firmware/config.txt"'
stdin, stdout, stderr = client.exec_command(cmd)
print("Add overlay STDERR:", stderr.read().decode())

# 2. Verify
stdin, stdout, stderr = client.exec_command('tail -5 /boot/firmware/config.txt')
print("Last 5 lines of config.txt:")
print(stdout.read().decode())

# 3. Reboot
print("Rebooting Pi...")
stdin, stdout, stderr = client.exec_command('echo 12345 | sudo -S reboot')
print("Reboot command sent!")

client.close()
