import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('sentinel.local', username='admin', password='12345', timeout=5)

# Upload the fixed app_pi.py
sftp = client.open_sftp()
sftp.put('app_pi.py', '/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py')
sftp.close()
print("Uploaded app.py")

# Restart gui service
stdin, stdout, stderr = client.exec_command('echo 12345 | sudo -S systemctl restart gui.service')
print("STDERR:", stderr.read().decode('utf-8', errors='replace'))
print("GUI service restarted!")

client.close()
