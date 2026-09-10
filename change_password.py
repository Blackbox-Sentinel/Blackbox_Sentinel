import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('sentinel.local', username='admin', password='12345', timeout=5)

new_password = "SentinelSecure#2026!"

# Use chpasswd to avoid interactive prompts
cmd = f'echo "admin:{new_password}" | sudo chpasswd'
stdin, stdout, stderr = client.exec_command(f'echo 12345 | sudo -S bash -c \'{cmd}\'')

print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

client.close()
