import paramiko
try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('sentinel.local', username='admin', password='12345', timeout=5)
    
    cmd = "python3 -c 'import serial; s=serial.Serial(\"/dev/ttyUSB0\", 115200, timeout=5); print(s.read(1000).decode(\"utf-8\", errors=\"ignore\"))'"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print('STDOUT:', stdout.read().decode())
    print('STDERR:', stderr.read().decode())
    client.close()
except Exception as e:
    print(e)
