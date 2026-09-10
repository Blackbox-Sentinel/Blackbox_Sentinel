import paramiko
import io

patch = """import sys
with open('/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py', 'r') as f:
    code = f.read()

target = 'ser.write(receipt_str.encode("utf-8"))'
replacement = '''ser.write(receipt_str.encode("utf-8"))
                    ser.flush()
                    import time
                    time.sleep(0.1)'''

if target in code and 'time.sleep(0.1)' not in code:
    code = code.replace(target, replacement)
    with open('/home/admin/blackbox-sentinel/m4-gui-venture/src/app.py', 'w') as f:
        f.write(code)
    print("Patched successfully")
else:
    print("Already patched or target not found")
"""

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('sentinel.local', username='admin', password='12345', timeout=5)
    
    sftp = client.open_sftp()
    sftp.putfo(io.BytesIO(patch.encode('utf-8')), '/home/admin/patch_app.py')
    sftp.close()
    
    stdin, stdout, stderr = client.exec_command('python3 /home/admin/patch_app.py && echo 12345 | sudo -S systemctl restart gui.service')
    print('STDOUT:', stdout.read().decode())
    print('STDERR:', stderr.read().decode())
    client.close()
except Exception as e:
    print(e)
