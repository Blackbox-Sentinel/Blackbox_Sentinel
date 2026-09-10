import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('sentinel.local', username='admin', password='12345', timeout=5)

# 1. Check if UART5 device exists
print("=== CHECKING UART5 ===")
stdin, stdout, stderr = client.exec_command('ls -la /dev/ttyAMA*')
print(stdout.read().decode())

# 2. Upload the fixed app_pi.py
sftp = client.open_sftp()
sftp.put('app_pi.py', '/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py')
sftp.close()
print("Uploaded app.py with UART5 fix")

# 3. Clear old debug log
stdin, stdout, stderr = client.exec_command('echo "" > /home/admin/mqtt_debug.log')
stdout.read()

# 4. Also start mosquitto back up for MQTT fallback
stdin, stdout, stderr = client.exec_command('echo 12345 | sudo -S systemctl start mosquitto')
stderr.read()
print("Mosquitto restarted (for MQTT fallback)")

# 5. Restart GUI
stdin, stdout, stderr = client.exec_command('echo 12345 | sudo -S systemctl restart gui.service')
print("STDERR:", stderr.read().decode())
print("GUI restarted!")

client.close()
