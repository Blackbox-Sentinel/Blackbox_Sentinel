import paramiko

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('sentinel.local', username='admin', password='12345', timeout=5)
    
    cmd = "mosquitto_pub -h localhost -t 'sentinel/c2_attack' -m '{\"payload\":{\"algorithm\":\"Ed25519\",\"decision\":\"CONTAIN\"}}' -d"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print('STDOUT:', stdout.read().decode())
    print('STDERR:', stderr.read().decode())
    client.close()
except Exception as e:
    print(e)
